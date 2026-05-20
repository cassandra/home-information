"""Frigate-shape HTTP API views (simulator-side).

Each view returns the JSON shape (or media-bytes shape) a real
Frigate instance would respond with, so HI's ``FrigateClient`` (and
the browser-side <img> tags HI emits for snapshots) can talk to the
simulator without any client-side branching.
"""
import logging
from datetime import datetime, timezone

from django.http import Http404, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hi.simulator.media import render_jpeg_frame
from hi.simulator.services.frigate.event_manager import FrigateSimEventManager
from hi.simulator.services.frigate.sim_models import FrigateCameraDetectState
from hi.simulator.services.frigate.simulator import FrigateSimulator

logger = logging.getLogger(__name__)


# Real Frigate's detect/set accepts these two values (case-sensitive
# uppercase). The simulator accepts either case as a defensive
# safety net against version drift on the integration side.
_FRIGATE_DETECT_STATES = { 'ON', 'OFF' }


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
class CameraDetectSetView( View ):
    """``POST /api/<camera_name>/detect/set`` — toggle per-camera
    object detection. Accepts a ``state`` query parameter; mirrors
    real Frigate's wire shape. The simulator is permissive on the
    state value's case (real Frigate is case-sensitive), since the
    HI side is the source of truth for the outbound value and we'd
    rather demonstrate the round-trip than enforce a wire
    convention. Returns 400 for an unknown state and 404 for an
    unknown camera so the HI client surfaces a clean error."""

    def post(self, request, camera_name : str, *args, **kwargs):
        state_value = request.GET.get( 'state' )
        if state_value is None:
            return JsonResponse(
                { 'error': 'Missing "state" query parameter.' },
                status = 400,
            )
        normalized_state = state_value.upper()
        if normalized_state not in _FRIGATE_DETECT_STATES:
            return JsonResponse(
                { 'error': f'Invalid state {state_value!r}; expected ON or OFF.' },
                status = 400,
            )

        simulator = FrigateSimulator()
        sim_camera = None
        for candidate in simulator.get_sim_cameras():
            if candidate.camera_name == camera_name:
                sim_camera = candidate
                break
            continue
        if sim_camera is None:
            raise Http404( f'Unknown Frigate camera: {camera_name!r}' )

        detect_state = sim_camera.detect_sim_state
        if detect_state is not None:
            simulator.set_sim_state(
                sim_entity_id = sim_camera.sim_entity.id,
                sim_state_id = FrigateCameraDetectState.DETECT_SIM_STATE_ID,
                value_str = normalized_state,
            )

        logger.info(
            'Frigate simulator received detect/set for %s: %s',
            camera_name, normalized_state,
        )
        return JsonResponse(
            { 'success': True, 'camera': camera_name, 'state': normalized_state },
        )


class EventSnapshotJpegView( View ):
    """``GET /api/events/<id>/snapshot.jpg`` — event snapshot.

    Real Frigate returns the single frame captured at the time of
    detection. HI attaches this URL to the OBJECT_PRESENCE
    SensorResponse as ``event_video_snapshot_url`` so the alert / history
    views can show what the camera saw. The simulator returns a
    placeholder JPEG stamped with the event id and label.

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
