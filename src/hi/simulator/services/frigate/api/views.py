"""Frigate-shape HTTP API views (simulator-side).

Each view returns the JSON shape (or media-bytes shape) a real
Frigate instance would respond with, so HI's ``FrigateClient`` (and
the browser-side <img> tags HI emits for snapshots) can talk to the
simulator without any client-side branching.
"""
import logging
import os
from datetime import datetime, timezone

from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.media import render_jpeg_frame
from hi.simulator.services.frigate.event_manager import FrigateSimEventManager
from hi.simulator.services.frigate.sim_models import FrigateCameraDetectState
from hi.simulator.services.frigate.simulator import FrigateSimulator


# Pre-generated short MP4 (~14 KB, H.264 baseline) ships alongside
# the simulator so the event-playback view shows a labeled,
# animated clip for every event without runtime media synthesis.
_EVENT_PLAYBACK_MP4_PATH = os.path.join(
    os.path.dirname( os.path.dirname( __file__ )),
    'static_assets', 'event_playback.mp4',
)

logger = logging.getLogger(__name__)


# Wire values for Frigate's detect-enabled config key on
# ``PUT /api/config/set``. Real Frigate parses these as JSON bool
# literals; the simulator accepts either case ("true"/"True"/"TRUE")
# as a defensive safety net against version drift on the integration
# side.
_FRIGATE_DETECT_ENABLED_TRUE_VALUES = { 'true' }
_FRIGATE_DETECT_ENABLED_FALSE_VALUES = { 'false' }
_FRIGATE_DETECT_ENABLED_CONFIG_KEY_PREFIX = 'cameras.'
_FRIGATE_DETECT_ENABLED_CONFIG_KEY_SUFFIX = '.detect.enabled'


def _apply_no_cache_headers( response ) -> None:
    """Snapshot URLs are cache-busted by HI with a timestamp param,
    but emit no-store headers as well so re-rendering an <img> tag
    with the same src in a stale cache still triggers a refetch."""
    response[ 'Cache-Control' ] = 'no-store, no-cache, must-revalidate, max-age=0'
    response[ 'Pragma' ] = 'no-cache'
    response[ 'Expires' ] = '0'
    return


class ConfigView( View ):
    """``GET /api/config`` — Frigate's effective configuration.

    Real Frigate returns a large nested document; HI's integration
    only cares about the ``cameras`` map (camera names are the keys).
    We emit the minimum shape the client needs plus a token of
    per-camera info so the response is recognizable as Frigate JSON.
    """

    def get(self, request, *args, **kwargs):
        try:
            simulator = FrigateSimulator()
            cameras = {}
            for sim_camera in simulator.get_sim_cameras():
                detect_state = sim_camera.detect_sim_state
                detect_enabled = (
                    detect_state.value == 'ON' if detect_state else True
                )
                cameras[ sim_camera.camera_name ] = {
                    'name': sim_camera.camera_name,
                    'friendly_name': sim_camera.display_name,
                    'enabled': True,
                    'detect': { 'enabled': detect_enabled },
                }
            return JsonResponse( { 'cameras': cameras } )
        except Exception:
            logger.exception( 'Problem processing Frigate /api/config request.' )
            return JsonResponse( { 'cameras': {} } )


class EventsListView( View ):
    """``GET /api/events`` — Frigate's events listing.

    v1 supports the ``after`` query parameter (epoch seconds), which
    is what the HI polling cursor will use. Other Frigate filters
    (``before`` / ``cameras`` / ``labels`` / ``zones``) are accepted
    and silently ignored — they're not on the HI integration's read
    path yet. Response is a top-level JSON array, most-recent
    start_time first (Frigate's convention)."""

    def get(self, request, *args, **kwargs):
        try:
            after_param = request.GET.get( 'after' )
            event_manager = FrigateSimEventManager()
            if after_param is not None:
                try:
                    after_epoch = float( after_param )
                except ValueError:
                    return JsonResponse(
                        { 'error': f'Invalid after parameter: {after_param!r}' },
                        status = 400,
                    )
                cutoff = datetime.fromtimestamp( after_epoch, tz = timezone.utc )
                events = event_manager.get_events_after( start_datetime = cutoff )
            else:
                events = event_manager.all_events()

            # Frigate orders events newest-first by start_time.
            events.sort( key = lambda e : e.start_datetime, reverse = True )
            return JsonResponse(
                [ e.to_api_dict() for e in events ],
                safe = False,
            )
        except Exception:
            logger.exception( 'Problem processing Frigate /api/events request.' )
            return JsonResponse( [], safe = False )


class EventDetailView( View ):
    """``GET /api/events/<id>`` — single Frigate event detail.

    Used by HI's integration to fetch event-specific data (snapshot
    URL, clip URL, full metadata). 404s for unknown ids so the HI
    client can distinguish "event doesn't exist" from "Frigate is
    broken"."""

    def get(self, request, event_id : str, *args, **kwargs):
        event = FrigateSimEventManager().find_event_by_id( event_id = event_id )
        if event is None:
            raise Http404( f'Unknown Frigate event id: {event_id!r}' )
        return JsonResponse( event.to_api_dict() )


class CameraLatestJpegView( View ):
    """``GET /api/<camera_name>/latest.jpg`` — live snapshot.

    Real Frigate returns the most recently decoded frame for the
    camera. The simulator returns a synthesized placeholder JPEG
    stamped with the camera name and current time so artifacts viewed
    inside HI are obviously coming from the simulator."""

    def get(self, request, camera_name : str, *args, **kwargs):
        text_lines = [ 'Live Snapshot (simulator)' ]
        sim_camera = self._find_sim_camera( camera_name = camera_name )
        if sim_camera is None:
            text_lines.append( f'camera "{camera_name}" (no record)' )
        else:
            text_lines.append( f'camera: {sim_camera.display_name}' )
            text_lines.append( f'name: {sim_camera.camera_name}' )
        response = HttpResponse(
            render_jpeg_frame( text_lines = text_lines ),
            content_type = 'image/jpeg',
        )
        _apply_no_cache_headers( response )
        return response

    @staticmethod
    def _find_sim_camera( camera_name : str ):
        for sim_camera in FrigateSimulator().get_sim_cameras():
            if sim_camera.camera_name == camera_name:
                return sim_camera
            continue
        return None


@method_decorator( csrf_exempt, name = 'dispatch' )
class ConfigSetView( View ):
    """``PUT /api/config/set`` — runtime config update.

    Real Frigate accepts a dotted-path key in the query string (e.g.
    ``cameras.<name>.detect.enabled=true``) and applies it to the
    persisted config. The simulator recognizes the
    detect-enabled key specifically and updates the camera's
    ``FrigateCameraDetectState`` sim-state so the operator observes
    the round-trip in the simulator UI. Other config keys are
    accepted but no-op; real Frigate would persist them but the
    simulator has no config to mutate. 400 on missing or invalid
    detect-enabled value; 404 on unknown camera."""

    def put(self, request, *args, **kwargs):
        # Find the detect-enabled key in the query string. Frigate's
        # config-set accepts multiple updates per call; we only
        # honor the detect-enabled one here.
        params = dict( request.GET.items() )
        detect_key = None
        detect_camera_name = None
        for key in params:
            if (
                key.startswith( _FRIGATE_DETECT_ENABLED_CONFIG_KEY_PREFIX )
                and key.endswith( _FRIGATE_DETECT_ENABLED_CONFIG_KEY_SUFFIX )
            ):
                detect_key = key
                detect_camera_name = key[
                    len( _FRIGATE_DETECT_ENABLED_CONFIG_KEY_PREFIX ):
                    -len( _FRIGATE_DETECT_ENABLED_CONFIG_KEY_SUFFIX )
                ]
                break
            continue
        if detect_key is None:
            return JsonResponse(
                { 'success': True, 'message': 'No simulator-honored keys in update.' },
            )

        raw_value = params[ detect_key ]
        normalized = raw_value.lower()
        if normalized in _FRIGATE_DETECT_ENABLED_TRUE_VALUES:
            new_state = 'ON'
        elif normalized in _FRIGATE_DETECT_ENABLED_FALSE_VALUES:
            new_state = 'OFF'
        else:
            return JsonResponse(
                {
                    'success': False,
                    'message': f'Invalid detect.enabled value {raw_value!r}; '
                               'expected true or false.',
                },
                status = 400,
            )

        simulator = FrigateSimulator()
        sim_camera = None
        for candidate in simulator.get_sim_cameras():
            if candidate.camera_name == detect_camera_name:
                sim_camera = candidate
                break
            continue
        if sim_camera is None:
            raise Http404( f'Unknown Frigate camera: {detect_camera_name!r}' )

        detect_state = sim_camera.detect_sim_state
        if detect_state is not None:
            simulator.set_sim_state(
                sim_entity_id = sim_camera.sim_entity.id,
                sim_state_id = FrigateCameraDetectState.DETECT_SIM_STATE_ID,
                value_str = new_state,
            )

        logger.info(
            'Frigate simulator received config/set for %s detect.enabled=%s',
            detect_camera_name, raw_value,
        )
        return JsonResponse(
            { 'success': True, 'message': 'Config successfully updated.' },
        )


class EventClipMp4View( View ):
    """``GET /api/events/<id>/clip.mp4`` — event clip playback.

    Real Frigate streams an MP4 of the event's clip. The simulator
    serves a fixed-content placeholder MP4 (frame-counter + clock
    overlay) so HI's Video Browse can demonstrate the round-trip
    without runtime media synthesis. 404s for unknown event ids."""

    def get(self, request, event_id : str, *args, **kwargs):
        event = FrigateSimEventManager().find_event_by_id( event_id = event_id )
        if event is None:
            raise Http404( f'Unknown Frigate event id: {event_id!r}' )
        response = FileResponse(
            open( _EVENT_PLAYBACK_MP4_PATH, 'rb' ),
            content_type = 'video/mp4',
        )
        _apply_no_cache_headers( response )
        return response


class EventSnapshotJpegView( View ):
    """``GET /api/events/<id>/snapshot.jpg`` — event snapshot.

    Real Frigate returns the single frame captured at the time of
    detection. HI's Frigate gateway builds this URL on demand from
    the event id (the SensorResponse carries the existence flag
    ``has_event_video_snapshot``) so the alert / history views can
    show what the camera saw. The simulator returns a placeholder
    JPEG stamped with the event id and label.

    404s for unknown event ids so the HI client distinguishes "event
    missing" from "simulator broken" — same posture as ``GET
    /api/events/<id>``."""

    def get(self, request, event_id : str, *args, **kwargs):
        event = FrigateSimEventManager().find_event_by_id( event_id = event_id )
        if event is None:
            raise Http404( f'Unknown Frigate event id: {event_id!r}' )
        text_lines = [
            'Event Snapshot (simulator)',
            f'camera: {event.camera_name}',
            f'event id: {event.event_id}',
            f'label: {event.label}',
        ]
        response = HttpResponse(
            render_jpeg_frame( text_lines = text_lines ),
            content_type = 'image/jpeg',
        )
        _apply_no_cache_headers( response )
        return response
