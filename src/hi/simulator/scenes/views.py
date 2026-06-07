import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common import datetimeproxy
from hi.simulator.profile.models import SimProfile
from hi.simulator.profile.profile_manager import ProfileManager
from hi.simulator.services.service_simulator_manager import ServiceSimulatorManager

from .models import SimScene, SimSceneBinding, SimSceneControl, SimStateSequence
from .player import SimPlayer
from .recorder import SimRecorder
from .scene_controller import SceneController
from .control_grid import control_key, resolve_control, simulator_by_module, split_control_key
from .initial_state import apply_initial_state, capture_current_state
from .sequence_io import parse_steps, safe_filename
from .transport import build_transport_context, transport_signature

logger = logging.getLogger(__name__)


def _scenes_redirect( scene_id = None, sequence_id = None ):
    url = reverse( 'simulator_scenes' )
    params = []
    if scene_id is not None:
        params.append( f'scene={scene_id}' )
    if sequence_id is not None:
        params.append( f'sequence={sequence_id}' )
    if params:
        url = f'{url}?' + '&'.join( params )
    return HttpResponseRedirect( url )


def _get_scene( scene_id ) -> SimScene:
    try:
        return SimScene.objects.get( id = scene_id )
    except SimScene.DoesNotExist:
        raise Http404( 'Scene not found.' )


class ScenesIndexView( View ):
    """The Scenes dashboard: compose a scene (per-module profile bindings),
    apply it, and drive the scene's curated state controls. (Record/
    playback lands in later phases.)"""

    def get( self, request, *args, **kwargs ):
        scene_list = list( SimScene.objects.all() )
        scene = self._resolve_selected_scene( request, scene_list )
        active_scene = SceneController().get_active_scene()

        context = {
            'active_section': 'scenes',
            'scene_list': scene_list,
            'scene': scene,
            'active_scene': active_scene,
            'module_rows': [],
            'control_grid': [],
            'missing_control_count': 0,
            'sequence_list': [],
            'selected_sequence': None,
            'recorder_status': SimRecorder().get_status(),
            'player_status': SimPlayer().get_status(),
            'timeline': None,
        }
        if scene is not None:
            simulator_by_module_map = simulator_by_module()
            context[ 'module_rows' ] = self._build_module_rows( scene, simulator_by_module_map )
            for control in scene.controls.all():
                resolved = resolve_control( control, simulator_by_module_map )
                if resolved is not None:
                    context[ 'control_grid' ].append( resolved )
                else:
                    context[ 'missing_control_count' ] += 1
                continue
            context.update( build_transport_context( scene, request.GET.get( 'sequence' )))
        return render( request, 'scenes/pages/scenes.html', context )

    def _resolve_selected_scene( self, request, scene_list ):
        scene_id = request.GET.get( 'scene' )
        if scene_id:
            try:
                return SimScene.objects.get( id = int( scene_id ))
            except ( ValueError, SimScene.DoesNotExist ):
                pass
        active = SceneController().get_active_scene()
        if active is not None:
            return active
        return scene_list[0] if scene_list else None

    def _build_module_rows( self, scene, simulator_by_module_map ):
        binding_by_module = {
            binding.module_key: binding
            for binding in scene.bindings.select_related( 'profile' ).all()
        }
        rows = []
        for module_key, simulator in simulator_by_module_map.items():
            binding = binding_by_module.get( module_key )
            rows.append({
                'module_key': module_key,
                'label': simulator.label,
                'profile_list': ProfileManager().list_profiles( module_key ),
                'bound_profile': binding.profile if binding else None,
            })
            continue
        rows.sort( key = lambda row : row['label'] )
        return rows


class SceneCreateView( View ):
    def post( self, request, *args, **kwargs ):
        name = ( request.POST.get( 'name' ) or '' ).strip()
        if not name:
            return _scenes_redirect()
        scene, _created = SimScene.objects.get_or_create( name = name )
        return _scenes_redirect( scene.id )


class SceneRenameView( View ):
    def post( self, request, scene_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        name = ( request.POST.get( 'name' ) or '' ).strip()
        if name:
            scene.name = name
            scene.save( update_fields = [ 'name' ] )
        return _scenes_redirect( scene.id )


class SceneDeleteView( View ):
    def post( self, request, scene_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        scene.delete()
        return _scenes_redirect()


class SceneApplyView( View ):
    """Apply the scene's profile bindings (clean baseline). If a sequence
    is currently selected, overlay its captured initial state on top so the
    operator lands at the sequence's intended starting point in one click."""

    def post( self, request, scene_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        SceneController().apply( scene )
        sequence_id = request.POST.get( 'sequence' )
        if sequence_id:
            try:
                sequence = SimStateSequence.objects.get(
                    id = int( sequence_id ), scene_id = scene.id,
                )
            except ( ValueError, SimStateSequence.DoesNotExist ):
                sequence = None
            if sequence is not None:
                apply_initial_state( sequence.initial_state_json or [] )
        return _scenes_redirect( scene.id, sequence_id or None )


class SceneOffView( View ):
    def post( self, request, *args, **kwargs ):
        SceneController().clear()
        return _scenes_redirect( request.POST.get( 'scene' ) )


class SceneClearStatesView( View ):
    """Reset the simulator's states to defaults and signal the (independent)
    main HI app to drop sensor responses from before now — so its lingering
    'recent/past' visuals don't force a wait before re-running a sequence.

    The two processes stay decoupled: the simulator only writes a cutoff epoch
    to the shared cache key; the main app owns reading/filtering it."""

    CUTOFF_TTL_SECS = 2 * 60 * 60  # past the main app's longest decay window

    def post( self, request, *args, **kwargs ):
        cache.set(
            settings.SENSOR_RESPONSE_CUTOFF_CACHE_KEY,
            datetimeproxy.now().timestamp(),
            self.CUTOFF_TTL_SECS,
        )
        ServiceSimulatorManager().reset_all_to_defaults()
        return antinode.refresh_response()


class SceneClearStatesConfirmView( View ):
    """Server-rendered confirmation modal for Clear States. Warns when the
    cutoff is disabled in settings, so the operator knows the main app will
    ignore it (simulator resets, but the console's recent/past won't clear)."""

    MODAL_TEMPLATE_NAME = 'scenes/modals/clear_states_confirm.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'cutoff_enabled': bool( getattr(
                settings, 'DEBUG_FORCE_SENSOR_RESPONSE_CUTOFF', False,
            )),
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )


class SceneRestoreStatesView( View ):
    """Complement to Clear States: drop the cutoff override from the shared
    cache so the main app reverts to normal (shows all cached sensor responses
    again). A debug aid for comparing cleared vs. normal behavior."""

    def post( self, request, *args, **kwargs ):
        cache.delete( settings.SENSOR_RESPONSE_CUTOFF_CACHE_KEY )
        return _scenes_redirect( request.POST.get( 'scene' ) )


class SceneBindingSetView( View ):
    """Set (or clear, with profile_id='none') the profile a module uses in
    a scene. GET-href driven, mirroring the existing profile-switch UI."""

    def get( self, request, scene_id, module_key, profile_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        if profile_id == 'none':
            SimSceneBinding.objects.filter(
                scene = scene, module_key = module_key,
            ).delete()
            return _scenes_redirect( scene.id )
        try:
            profile = SimProfile.objects.get(
                id = int( profile_id ), module_key = module_key,
            )
        except ( ValueError, SimProfile.DoesNotExist ):
            raise Http404( 'Profile not found for module.' )
        SimSceneBinding.objects.update_or_create(
            scene = scene, module_key = module_key,
            defaults = { 'profile': profile },
        )
        return _scenes_redirect( scene.id )


class SceneEditStatesView( View ):
    """Curate the scene's dashboard control set: a modal of all currently
    loaded states as checkboxes; checked items become SimSceneControl rows
    (in submission order). Lists currently-loaded states, so apply the
    scene first if its entities aren't loaded yet."""

    MODAL_TEMPLATE_NAME = 'scenes/modals/edit_states.html'

    def get( self, request, scene_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        context = {
            'scene': scene,
            'module_state_tree': self._build_state_tree( scene ),
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post( self, request, scene_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        keys = request.POST.getlist( 'state' )
        with transaction.atomic():
            scene.controls.all().delete()
            controls = []
            for order_id, key in enumerate( keys ):
                module_key, entity_name, sim_state_id = split_control_key( key )
                controls.append( SimSceneControl(
                    scene = scene,
                    module_key = module_key,
                    entity_name = entity_name,
                    sim_state_id = sim_state_id,
                    order_id = order_id,
                ))
                continue
            SimSceneControl.objects.bulk_create( controls )
        return antinode.refresh_response()

    def _build_state_tree( self, scene ):
        selected_keys = {
            control_key( c.module_key, c.entity_name, c.sim_state_id )
            for c in scene.controls.all()
        }
        tree = []
        dom_counter = 0
        for simulator_data in ServiceSimulatorManager().get_simulator_data_list():
            simulator = simulator_data.simulator
            entities = []
            for sim_entity in simulator.sim_entities:
                states = []
                for sim_state in sim_entity.sim_state_list:
                    key = control_key(
                        simulator.module_key, sim_entity.name, sim_state.sim_state_id,
                    )
                    dom_counter += 1
                    states.append({
                        'dom_id': f'edit-state-{dom_counter}',
                        'key': key,
                        'name': sim_state.name,
                        'selected': key in selected_keys,
                    })
                    continue
                if states:
                    entities.append({ 'name': sim_entity.name, 'states': states })
                continue
            if entities:
                tree.append({ 'label': simulator.label, 'entities': entities })
            continue
        return tree


class SceneRecordStartView( View ):
    """Apply the scene's clean baseline, then start recording so the
    captured sequence is reproducible (playback applies the same baseline
    before replaying steps). If a sequence is currently selected, overlay
    its captured initial state too — re-records of a beat sequence start
    from the same starting world the playback would."""

    def post( self, request, scene_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        SceneController().apply( scene )
        sequence_id = request.POST.get( 'sequence' )
        if sequence_id:
            try:
                sequence = SimStateSequence.objects.get(
                    id = int( sequence_id ), scene_id = scene.id,
                )
            except ( ValueError, SimStateSequence.DoesNotExist ):
                sequence = None
            if sequence is not None:
                apply_initial_state( sequence.initial_state_json or [] )
        SimRecorder().start( scene )
        return _scenes_redirect( scene.id, sequence_id or None )


class SceneStopView( View ):
    """Single STOP for both recording and playback (per the UI)."""

    def post( self, request, scene_id, *args, **kwargs ):
        SimRecorder().stop()
        SimPlayer().stop()
        return _scenes_redirect( scene_id, request.POST.get( 'sequence' ) )


class SceneRecordSaveView( View ):
    def post( self, request, scene_id, *args, **kwargs ):
        sequence = SimRecorder().save( request.POST.get( 'name' ) )
        return _scenes_redirect(
            scene_id, sequence.id if sequence is not None else None,
        )


class SceneRecordDiscardView( View ):
    def post( self, request, scene_id, *args, **kwargs ):
        SimRecorder().discard()
        return _scenes_redirect( scene_id )


def _get_sequence( scene_id, sequence_id ) -> SimStateSequence:
    try:
        return SimStateSequence.objects.get( id = sequence_id, scene_id = scene_id )
    except SimStateSequence.DoesNotExist:
        raise Http404( 'Sequence not found.' )


class ScenePlayView( View ):
    def post( self, request, scene_id, sequence_id, *args, **kwargs ):
        SimPlayer().play( _get_sequence( scene_id, sequence_id ))
        return _scenes_redirect( scene_id, sequence_id )


class SceneStepView( View ):
    def post( self, request, scene_id, sequence_id, *args, **kwargs ):
        SimPlayer().step( _get_sequence( scene_id, sequence_id ))
        return _scenes_redirect( scene_id, sequence_id )


class SceneSeekView( View ):
    def post( self, request, scene_id, sequence_id, *args, **kwargs ):
        sequence = _get_sequence( scene_id, sequence_id )
        try:
            t = float( request.POST.get( 't' ) or 0.0 )
        except ( TypeError, ValueError ):
            t = 0.0
        SimPlayer().seek( sequence, t )
        return _scenes_redirect( scene_id, sequence_id )


class ScenePauseView( View ):
    """Single PAUSE: toggles the record clock while recording, otherwise
    pauses playback."""

    def post( self, request, scene_id, *args, **kwargs ):
        recorder = SimRecorder()
        if recorder.is_recording():
            recorder.toggle_pause()
        else:
            SimPlayer().pause()
        return _scenes_redirect( scene_id, request.POST.get( 'sequence' ))


class SceneMarkView( View ):
    """Single MARK (paused only): marks the recording while recording,
    otherwise marks the loaded playback sequence."""

    def post( self, request, scene_id, *args, **kwargs ):
        name = request.POST.get( 'name' )
        recorder = SimRecorder()
        if recorder.is_recording():
            recorder.mark( name )
            return _scenes_redirect( scene_id )
        SimPlayer().mark( name )
        return _scenes_redirect( scene_id, request.POST.get( 'sequence' ))


class SequenceDeleteView( View ):
    def post( self, request, sequence_id, *args, **kwargs ):
        try:
            sequence = SimStateSequence.objects.get( id = sequence_id )
        except SimStateSequence.DoesNotExist:
            raise Http404( 'Sequence not found.' )
        scene_id = sequence.scene_id
        sequence.delete()
        return _scenes_redirect( scene_id )


class SequenceSetInitialView( View ):
    """Snapshot all currently-loaded sim states and save them as the
    sequence's initial-state overlay. Refreshes the page so the operator
    sees the updated count badge in the transport pane."""

    def post( self, request, sequence_id, *args, **kwargs ):
        try:
            sequence = SimStateSequence.objects.get( id = sequence_id )
        except SimStateSequence.DoesNotExist:
            raise Http404( 'Sequence not found.' )
        sequence.initial_state_json = capture_current_state()
        sequence.save( update_fields = [ 'initial_state_json', 'updated_datetime' ] )
        return _scenes_redirect( sequence.scene_id, sequence.id )


class SequenceClearInitialView( View ):
    """Wipe the sequence's initial-state overlay so it loads against pure
    profile baseline."""

    def post( self, request, sequence_id, *args, **kwargs ):
        try:
            sequence = SimStateSequence.objects.get( id = sequence_id )
        except SimStateSequence.DoesNotExist:
            raise Http404( 'Sequence not found.' )
        sequence.initial_state_json = []
        sequence.save( update_fields = [ 'initial_state_json', 'updated_datetime' ] )
        return _scenes_redirect( sequence.scene_id, sequence.id )


class SceneSequenceEditView( View ):
    """Rename a sequence and/or edit its raw step JSON (markers + timing)."""

    MODAL_TEMPLATE_NAME = 'scenes/modals/edit_sequence.html'

    def get( self, request, scene_id, sequence_id, *args, **kwargs ):
        sequence = _get_sequence( scene_id, sequence_id )
        context = {
            'scene': sequence.scene,
            'sequence': sequence,
            'name_value': sequence.name,
            'steps_text': json.dumps( sequence.steps_json or [], indent = 2 ),
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post( self, request, scene_id, sequence_id, *args, **kwargs ):
        sequence = _get_sequence( scene_id, sequence_id )
        name = ( request.POST.get( 'name' ) or '' ).strip()
        raw = request.POST.get( 'steps' ) or ''
        steps, error = parse_steps( raw )
        if not error and not name:
            error = 'Name is required.'
        if not error and SimStateSequence.objects.filter(
                scene = sequence.scene, name = name ).exclude( id = sequence.id ).exists():
            error = 'A sequence with that name already exists.'
        if error:
            return render( request, self.MODAL_TEMPLATE_NAME, {
                'scene': sequence.scene,
                'sequence': sequence,
                'name_value': name or sequence.name,
                'steps_text': raw,
                'error': error,
            })
        sequence.name = name
        sequence.steps_json = steps
        sequence.save()
        return antinode.refresh_response()


class SceneSequenceExportView( View ):
    def get( self, request, scene_id, sequence_id, *args, **kwargs ):
        sequence = _get_sequence( scene_id, sequence_id )
        payload = { 'name': sequence.name, 'steps': sequence.steps_json or [] }
        response = HttpResponse(
            json.dumps( payload, indent = 2 ),
            content_type = 'application/json',
        )
        response[ 'Content-Disposition' ] = (
            f'attachment; filename="{safe_filename( sequence.name )}.json"'
        )
        return response


class SceneSequenceImportView( View ):
    """Create a new sequence from a pasted/uploaded export (or bare step list)."""

    MODAL_TEMPLATE_NAME = 'scenes/modals/import_sequence.html'

    def get( self, request, scene_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        return render( request, self.MODAL_TEMPLATE_NAME, { 'scene': scene } )

    def post( self, request, scene_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        upload = request.FILES.get( 'file' )
        if upload is not None:
            raw = upload.read().decode( 'utf-8', errors = 'replace' )
        else:
            raw = request.POST.get( 'steps' ) or ''
        steps, error = parse_steps( raw )
        name = ( request.POST.get( 'name' ) or '' ).strip() or self._name_from_payload( raw )
        if not name:
            name = f'Sequence {scene.state_sequences.count() + 1}'
        if not error:
            while SimStateSequence.objects.filter( scene = scene, name = name ).exists():
                name = f'{name} (imported)'
        if error:
            return render( request, self.MODAL_TEMPLATE_NAME, {
                'scene': scene,
                'name_value': name,
                'steps_text': raw,
                'error': error,
            })
        SimStateSequence.objects.create(
            scene = scene, name = name, steps_json = steps,
        )
        return antinode.refresh_response()

    def _name_from_payload( self, raw ):
        try:
            payload = json.loads( raw )
        except ( ValueError, TypeError ):
            return ''
        if isinstance( payload, dict ):
            return ( payload.get( 'name' ) or '' ).strip()
        return ''


class SceneStatusView( View ):
    """Lightweight JSON poll for live transport: player/recorder status plus a
    button-relevant signature the client uses to decide when to fragment-
    refresh the transport pane. Player/recorder are process singletons, so
    this needs no scene id."""

    def get( self, request, *args, **kwargs ):
        recorder_status = SimRecorder().get_status()
        player_status = SimPlayer().get_status()
        return JsonResponse({
            'signature': transport_signature( recorder_status, player_status ),
            'player': {
                'mode': player_status[ 'mode' ],
                'playing': player_status[ 'playing' ],
                'paused': player_status[ 'paused' ],
                'playhead': player_status[ 'playhead' ],
                'playhead_limit': player_status[ 'playhead_limit' ],
                'total': player_status[ 'total' ],
                'sequence_id': player_status[ 'sequence_id' ],
            },
            'recorder': {
                'recording': recorder_status[ 'recording' ],
                'paused': recorder_status[ 'paused' ],
                'step_count': recorder_status[ 'step_count' ],
                'has_working': recorder_status[ 'has_working' ],
            },
        })


class SceneTransportView( View ):
    """Render just the transport pane (badge, controls, timeline) for live
    fragment-refresh when the transport signature changes."""

    def get( self, request, scene_id, *args, **kwargs ):
        scene = _get_scene( scene_id )
        context = build_transport_context( scene, request.GET.get( 'sequence' ))
        return render( request, 'scenes/panes/transport.html', context )
