"""Shared synthetic-media primitives for the simulator.

Both the ZoneMinder and Home Assistant simulators need to serve a
single placeholder JPEG (event snapshot thumbnail / camera snapshot)
with operator-identifying text overlaid so the artifact viewed inside
HI is obviously coming from the simulator and from a specific entity.

This module owns that one primitive; per-integration media modules
(e.g., ``zm_media.py``) wrap it with their own framing conventions.
"""
import io
from datetime import datetime
from typing import List, Optional

from PIL import Image, ImageDraw

import hi.apps.common.datetimeproxy as datetimeproxy


# Modest default size — recognizable text overlay, low render cost.
FRAME_WIDTH = 320
FRAME_HEIGHT = 240


def render_jpeg_frame(
        text_lines         : List[str],
        timestamp_override : Optional[datetime] = None,
) -> bytes:
    """Pillow-rendered single JPEG frame. Default bitmap font so the
    simulator stays independent of system font availability. The
    timestamp line is appended automatically so multiple frames
    rendered in quick succession still differ visibly. When
    ``timestamp_override`` is provided (event playback), that value
    is rendered instead of wall-clock now."""
    raw_timestamp = (
        timestamp_override if timestamp_override is not None else datetimeproxy.now()
    )
    timestamp = raw_timestamp.strftime( '%Y-%m-%d %H:%M:%S' )
    image = Image.new(
        mode = 'RGB',
        size = ( FRAME_WIDTH, FRAME_HEIGHT ),
        color = ( 25, 30, 50 ),
    )
    draw = ImageDraw.Draw( image )
    y = 30
    for line in text_lines:
        draw.text( ( 20, y ), line, fill = ( 230, 240, 250 ) )
        y += 24
    draw.text( ( 20, FRAME_HEIGHT - 30 ), timestamp, fill = ( 150, 170, 200 ) )
    draw.text( ( FRAME_WIDTH - 110, FRAME_HEIGHT - 30 ),
               '(simulator)', fill = ( 120, 130, 150 ) )
    buffer = io.BytesIO()
    image.save( buffer, format = 'JPEG', quality = 70 )
    return buffer.getvalue()
