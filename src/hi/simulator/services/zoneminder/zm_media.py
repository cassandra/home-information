"""
Synthetic ZoneMinder media generation for the simulator.

ZoneMinder serves three byte-shapes the HI integration consumes:

  1. Event snapshot thumbnails — single JPEG via
     ``index.php?view=image&eid=<id>&fid=snapshot``.

  2. Event playback — a *bounded* MJPEG stream
     (``multipart/x-mixed-replace`` response containing N JPEG
     parts) via ``cgi-bin/nph-zms?...&source=event&event=<id>``.

  3. Live camera feed — same MJPEG shape via
     ``cgi-bin/nph-zms?...&monitor=<id>``.

The simulator collapses all three into the same primitives:
``render_jpeg_frame`` (lifted to ``hi.simulator.media`` so both
ZM and HA snapshots share it) and ``iter_bounded_mjpeg_parts``
(yields each multipart chunk with a delay between frames so the
browser's MJPEG renderer animates through them rather than
collapsing to the last frame). The "live" stream is bounded too —
it cycles through a fixed frame count and ends — which is enough
to exercise the HI player's wiring without holding a long-running
connection open against Django's dev server.

Frame content carries operator-visible identifiers (monitor name,
event id, frame number, current time) so that artifacts viewed
inside HI are obviously coming from the simulator and from which
specific monitor/event.
"""
import time
from datetime import datetime, timedelta
from typing import Iterator, List, Optional, Tuple

from hi.simulator.media import render_jpeg_frame


# Single boundary string is reused across all MJPEG responses; the
# bytes are arbitrary as long as they don't appear in the JPEG
# payload (JPEGs start with ``\xff\xd8`` and end with ``\xff\xd9``,
# and never contain the literal "ZmSimulatorMjpegBoundary" string).
_MJPEG_BOUNDARY = b'ZmSimulatorMjpegBoundary'

# Fixed frame count for bounded MJPEG. Small enough to keep each
# stream short, large enough that the operator sees the player
# animate before the response ends.
_DEFAULT_FRAME_COUNT = 8

# Inter-frame delay. Real ZoneMinder MJPEG runs around 5 fps; we
# slow it slightly so the "(simulator)" frame counter is readable.
_DEFAULT_FRAME_INTERVAL_SECS = 0.5


def render_thumbnail_jpeg( text_lines : List[str] ) -> bytes:
    """Single placeholder JPEG used as an event snapshot thumbnail.
    ``text_lines`` is rendered in stacked rows; callers typically
    pass the monitor name, event id, and timestamp so the
    artifact is identifiable inside HI."""
    return render_jpeg_frame( text_lines = text_lines )


def mjpeg_content_type() -> str:
    """``Content-Type`` header value pairing the streamed body with
    its multipart boundary."""
    return (
        f'multipart/x-mixed-replace; boundary={_MJPEG_BOUNDARY.decode("latin-1")}'
    )


def _mjpeg_part( jpeg_bytes : bytes ) -> bytes:
    """One ``multipart/x-mixed-replace`` chunk wrapping a JPEG frame."""
    return (
        b'--' + _MJPEG_BOUNDARY + b'\r\n'
        + b'Content-Type: image/jpeg\r\n'
        + f'Content-Length: {len(jpeg_bytes)}\r\n\r\n'.encode( 'latin-1' )
        + jpeg_bytes
        + b'\r\n'
    )


def iter_mjpeg_parts_from_frames(
        jpeg_frames    : Iterator[ bytes ],
        frame_interval : float             = _DEFAULT_FRAME_INTERVAL_SECS,
) -> Iterator[ bytes ]:
    """Bounded MJPEG from pre-rendered JPEG frames (real pre-canned footage),
    sleeping between frames so the browser animates rather than collapsing to
    the last frame. Mirrors ``iter_bounded_mjpeg_parts`` but serves given
    frames instead of synthesized placeholders."""
    for jpeg_bytes in jpeg_frames:
        yield _mjpeg_part( jpeg_bytes )
        time.sleep( frame_interval )
        continue
    yield b'--' + _MJPEG_BOUNDARY + b'--\r\n'


def iter_bounded_mjpeg_parts(
        text_lines           : List[str],
        frame_count          : int               = _DEFAULT_FRAME_COUNT,
        frame_interval       : float             = _DEFAULT_FRAME_INTERVAL_SECS,
        playback_start       : Optional[datetime] = None,
        playback_duration    : Optional[float]    = None,
) -> Iterator[ bytes ]:
    """Yield multipart chunks for a bounded MJPEG stream — one
    boundary+headers+JPEG body per frame, with a sleep between
    frames so the browser's MJPEG renderer actually animates.
    Without the sleep the parts arrive in a single TCP burst and
    the renderer collapses to the last frame.

    ``playback_start`` + ``playback_duration`` (when both provided)
    interpolate a frame timestamp across the playback window so an
    event replay shows the event's actual time progression rather
    than wall-clock now. When omitted, frames stamp the current
    time — the right behavior for a live feed.

    Used with ``StreamingHttpResponse``; pair the iterator with
    ``mjpeg_content_type()`` for the response header. Total stream
    duration is ``frame_count * frame_interval``; the connection
    closes naturally after the last frame so we don't hold an
    open-ended live feed against the Django dev server.
    """
    for index in range( frame_count ):
        frame_text = list( text_lines ) + [
            f'frame {index + 1}/{frame_count}',
        ]
        jpeg_bytes = render_jpeg_frame(
            text_lines = frame_text,
            timestamp_override = _interpolated_frame_time(
                playback_start = playback_start,
                playback_duration = playback_duration,
                index = index,
                frame_count = frame_count,
            ),
        )
        yield _mjpeg_part( jpeg_bytes )
        # Sleep AFTER yielding the frame so the browser sees a
        # cadence between frames; the final frame still gets
        # displayed for ``frame_interval`` before the closing
        # boundary tells the browser the stream has ended.
        time.sleep( frame_interval )
        continue
    yield b'--' + _MJPEG_BOUNDARY + b'--\r\n'


def _interpolated_frame_time(
        playback_start    : Optional[datetime],
        playback_duration : Optional[float],
        index             : int,
        frame_count       : int,
) -> Optional[datetime]:
    """Linearly interpolate a frame's timestamp across the playback
    window. Frame 0 lands at ``playback_start``; the last frame
    lands at ``playback_start + playback_duration``. Returns None
    when either bound is missing — the renderer then falls back to
    wall-clock time."""
    if playback_start is None or playback_duration is None:
        return None
    if frame_count <= 1:
        return playback_start
    progress = index / ( frame_count - 1 )
    return playback_start + timedelta( seconds = playback_duration * progress )


# Backward-compatible non-streaming variant kept for callers that
# want a single bytes blob (e.g., tests). Note that delivering this
# in one HttpResponse causes browsers to render only the last frame
# — use ``iter_bounded_mjpeg_parts`` + ``StreamingHttpResponse`` for
# anything the operator will actually view.
def render_bounded_mjpeg_response(
        text_lines       : List[str],
        frame_count      : int = _DEFAULT_FRAME_COUNT,
) -> Tuple[ bytes, str ]:
    body = b''.join(
        iter_bounded_mjpeg_parts(
            text_lines = text_lines,
            frame_count = frame_count,
            frame_interval = 0.0,
        )
    )
    return body, mjpeg_content_type()
