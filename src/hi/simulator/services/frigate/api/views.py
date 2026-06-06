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
from django.views.generic import View

from hi.simulator.media import render_jpeg_frame
from hi.simulator.services.frigate.event_history import camera_name_from_event_id
from hi.simulator.services.frigate.event_manager import FrigateSimEventManager
from hi.simulator.services.frigate.simulator import FrigateSimulator
from hi.simulator.video_playback.video_clip_manager import VideoClipManager


# Pre-generated short MP4 (~14 KB, H.264 baseline) ships alongside
# the simulator so the event-playback view shows a labeled,
# animated clip for every event without runtime media synthesis.
_EVENT_PLAYBACK_MP4_PATH = os.path.join(
    os.path.dirname( os.path.dirname( __file__ )),
    'static_assets', 'event_playback.mp4',
)

logger = logging.getLogger(__name__)


def _apply_no_cache_headers( response ) -> None:
    """Snapshot URLs are cache-busted by HI with a timestamp param,
    but emit no-store headers as well so re-rendering an <img> tag
    with the same src in a stale cache still triggers a refetch."""
    response[ 'Cache-Control' ] = 'no-store, no-cache, must-revalidate, max-age=0'
    response[ 'Pragma' ] = 'no-cache'
    response[ 'Expires' ] = '0'
    return


def _find_sim_camera( camera_name : str ):
    for sim_camera in FrigateSimulator().get_sim_cameras():
        if sim_camera.camera_name == camera_name:
            return sim_camera
        continue
    return None


def _find_sim_camera_for_event( event_id : str ):
    """Resolve the camera for an event-media request from the event id alone
    (the id encodes the camera name), so it works even for historical events
    the ephemeral event manager no longer holds. None when the id predates the
    camera-encoded format or the camera no longer exists."""
    camera_name = camera_name_from_event_id( event_id )
    if camera_name is None:
        return None
    return _find_sim_camera( camera_name = camera_name )


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
                cameras[ sim_camera.camera_name ] = {
                    'name': sim_camera.camera_name,
                    'friendly_name': sim_camera.display_name,
                    'enabled': True,
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
        sim_camera = _find_sim_camera( camera_name = camera_name )

        # Serve a frame from the selected live clip; fall through to the
        # synthesized placeholder when "synthetic" (or the clip is missing).
        frame_bytes = None
        if sim_camera is not None:
            frame_bytes = VideoClipManager().live_frame_bytes( sim_camera.live_clip )
        if frame_bytes is None:
            text_lines = [ 'Live Snapshot (simulator)' ]
            if sim_camera is None:
                text_lines.append( f'camera "{camera_name}" (no record)' )
            else:
                text_lines.append( f'camera: {sim_camera.display_name}' )
                text_lines.append( f'name: {sim_camera.camera_name}' )
            frame_bytes = render_jpeg_frame( text_lines = text_lines )

        response = HttpResponse( frame_bytes, content_type = 'image/jpeg' )
        _apply_no_cache_headers( response )
        return response


class EventClipMp4View( View ):
    """``GET /api/events/<id>/clip.mp4`` — event clip playback.

    Serves the pre-rendered ``clip.mp4`` of the event camera's selected
    ``event_clip`` (built offline by the import tool — no runtime transcoding).
    Falls back to the fixed-content placeholder MP4 when the clip has no mp4,
    the selection is ``synthetic``, or the event is unknown.

    Unknown event ids are NOT 404'd: HI history/alarms persist and can
    reference events the (ephemeral, in-memory) simulator no longer has after
    a restart, and a 404 here renders as an unplayable ``<video>`` ("No video
    with supported format")."""

    def get(self, request, event_id : str, *args, **kwargs):
        mp4_path = None
        sim_camera = _find_sim_camera_for_event( event_id )
        if sim_camera is not None:
            mp4_path = VideoClipManager().clip_mp4_path( sim_camera.event_clip )
        if mp4_path is None:
            mp4_path = _EVENT_PLAYBACK_MP4_PATH

        response = FileResponse( open( mp4_path, 'rb' ), content_type = 'video/mp4' )
        _apply_no_cache_headers( response )
        return response


class EventSnapshotJpegView( View ):
    """``GET /api/events/<id>/snapshot.jpg`` — event snapshot.

    Real Frigate returns the single frame captured at the time of
    detection. HI's Frigate gateway builds this URL on demand from
    the event id (the SensorResponse carries the existence flag
    ``has_event_video_snapshot``) so the alert / history views can
    show what the camera saw.

    Unknown event ids are NOT 404'd (a 404 renders as a broken ``<img>``):
    HI history/alarms persist and can reference events the (ephemeral,
    in-memory) simulator no longer has after a restart. Serve the event
    camera's selected event-clip frame when the event is known; otherwise a
    placeholder."""

    def get(self, request, event_id : str, *args, **kwargs):
        frame_bytes = None
        sim_camera = _find_sim_camera_for_event( event_id )
        if sim_camera is not None:
            frame_bytes = VideoClipManager().event_frame_bytes( sim_camera.event_clip )
        if frame_bytes is None:
            frame_bytes = render_jpeg_frame( text_lines = [
                'Event Snapshot (simulator)',
                f'event id: {event_id}',
            ] )

        response = HttpResponse( frame_bytes, content_type = 'image/jpeg' )
        _apply_no_cache_headers( response )
        return response
