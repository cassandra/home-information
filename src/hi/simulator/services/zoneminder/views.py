"""
Top-level (non-API) ZoneMinder simulator views.

ZoneMinder serves more than the JSON ``api/`` endpoints; the HI
integration also points at portal-level URLs for media:

  * ``index.php?view=image&eid=<id>&fid=snapshot`` — single-JPEG
    event thumbnail.
  * ``cgi-bin/nph-zms?...&monitor=<id>``           — live MJPEG.
  * ``cgi-bin/nph-zms?...&source=event&event=<id>`` — event playback
    MJPEG.

These endpoints respond with synthetic Pillow-rendered placeholder
frames (see ``zm_media``). The MJPEG flavors are bounded — the
response body contains a small fixed number of frames and a closing
boundary, so the client cycles once and stops on the last frame.
That's enough to exercise the HI player wiring without holding
long-lived streams open against Django's dev server.
"""
from django.http import HttpResponse, StreamingHttpResponse
from django.views.generic import View

from .simulator import ZoneMinderSimulator
from .zm_event_manager import ZmSimEventManager
from .zm_media import (
    iter_bounded_mjpeg_parts,
    mjpeg_content_type,
    render_thumbnail_jpeg,
)


class HomeView( View ):

    def get(self, request, *args, **kwargs):
        pass


class IndexPhpView( View ):
    """Dispatch on the ``view`` query parameter. Real ZoneMinder's
    ``index.php`` is a multi-purpose entry point; we only honor
    ``view=image`` (used by the integration to fetch event
    thumbnails) and 404 anything else so unsupported portal paths
    don't silently render an empty body."""

    def get(self, request, *args, **kwargs):
        view_param = request.GET.get( 'view' )
        if view_param == 'image':
            return _event_image_response( request )
        return HttpResponse(
            f'Unsupported view "{view_param}".',
            status = 404,
            content_type = 'text/plain',
        )


class NphZmsView( View ):
    """``cgi-bin/nph-zms`` MJPEG endpoint. The HI integration emits
    two URL flavors against this path:

      * ``source=event&event=<id>`` — event playback. Frames
        identify the monitor + event id.

      * ``monitor=<id>`` (no event params) — live feed. Frames
        identify the monitor.

    Both flavors return a bounded ``multipart/x-mixed-replace``
    response (single body containing N JPEG parts followed by a
    closing boundary). See ``zm_media`` for rationale on the
    bounded shape.
    """

    def get(self, request, *args, **kwargs):
        event_id_str = request.GET.get( 'event' )
        if event_id_str is not None:
            return self._event_playback_response( event_id_str = event_id_str )

        monitor_id_str = request.GET.get( 'monitor' )
        if monitor_id_str is not None:
            return self._live_stream_response( monitor_id_str = monitor_id_str )

        return HttpResponse(
            'nph-zms requires monitor or event query parameter.',
            status = 400,
            content_type = 'text/plain',
        )

    def _event_playback_response( self, event_id_str : str ) -> StreamingHttpResponse:
        text_lines = [ 'Event Playback (simulator)' ]
        playback_start = None
        playback_duration = None
        try:
            event_id = int( event_id_str )
        except ValueError:
            text_lines.append( f'unknown event "{event_id_str}"' )
        else:
            zm_sim_event = ZmSimEventManager().find_event_by_id( event_id = event_id )
            if zm_sim_event is None:
                text_lines.append( f'event {event_id} (no record)' )
            else:
                text_lines.append(
                    f'monitor: {zm_sim_event.zm_sim_monitor.name}',
                )
                text_lines.append( f'event id: {event_id}' )
                playback_start = zm_sim_event.start_datetime
                # ``length_secs`` is an event-driven value the
                # simulator updates as the event is closed; it can
                # legitimately be 0 for an event that opened and
                # closed in the same poll. Fall back to a small
                # nonzero window so the interpolated frame times
                # still show motion.
                playback_duration = (
                    zm_sim_event.length_secs if zm_sim_event.length_secs else 1.0
                )
        return _streaming_mjpeg_response(
            text_lines = text_lines,
            playback_start = playback_start,
            playback_duration = playback_duration,
        )

    def _live_stream_response( self, monitor_id_str : str ) -> StreamingHttpResponse:
        text_lines = [ 'Live Stream (simulator)' ]
        try:
            monitor_id = int( monitor_id_str )
        except ValueError:
            text_lines.append( f'unknown monitor "{monitor_id_str}"' )
        else:
            zm_sim_monitor = ZoneMinderSimulator().find_zm_monitor_by_id(
                monitor_id = monitor_id,
            )
            if zm_sim_monitor is None:
                text_lines.append( f'monitor {monitor_id} (no record)' )
            else:
                text_lines.append( f'monitor: {zm_sim_monitor.name}' )
                text_lines.append( f'id: {monitor_id}' )
        return _streaming_mjpeg_response( text_lines = text_lines )


def _streaming_mjpeg_response(
        text_lines,
        playback_start = None,
        playback_duration = None,
) -> StreamingHttpResponse:
    """Build the StreamingHttpResponse for an MJPEG endpoint with
    cache-busting headers. Without ``no-store`` the browser caches
    the multipart response and replays it instantly on the next
    fetch, which collapses the rendered animation to the last frame
    (the renderer sees all parts arrive in one tick). Real
    ZoneMinder also emits no-cache headers for the same reason.

    ``playback_start`` + ``playback_duration``, when provided, make
    the rendered frame timestamps span the event's actual time
    window instead of wall-clock now (event-replay flavor)."""
    response = StreamingHttpResponse(
        iter_bounded_mjpeg_parts(
            text_lines = text_lines,
            playback_start = playback_start,
            playback_duration = playback_duration,
        ),
        content_type = mjpeg_content_type(),
    )
    _apply_no_cache_headers( response )
    return response


def _apply_no_cache_headers( response ) -> None:
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return


def _event_image_response( request ) -> HttpResponse:
    event_id_str = request.GET.get( 'eid' )
    text_lines = [ 'Event Snapshot (simulator)' ]
    try:
        event_id = int( event_id_str ) if event_id_str else None
    except ValueError:
        event_id = None
    if event_id is None:
        text_lines.append( f'unknown event "{event_id_str}"' )
    else:
        zm_sim_event = ZmSimEventManager().find_event_by_id( event_id = event_id )
        if zm_sim_event is None:
            text_lines.append( f'event {event_id} (no record)' )
        else:
            text_lines.append( f'monitor: {zm_sim_event.zm_sim_monitor.name}' )
            text_lines.append( f'event id: {event_id}' )
    response = HttpResponse(
        render_thumbnail_jpeg( text_lines = text_lines ),
        content_type = 'image/jpeg',
    )
    _apply_no_cache_headers( response )
    return response
