"""Shared synthetic-media primitives for the simulator.

Renders a placeholder JPEG with operator-identifying text overlaid
so the image viewed inside HI is obviously synthetic. Also provides
generic placeholder image and PDF builders used by service-specific
attachment catalogs.
"""
import io
from datetime import datetime
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw

import hi.apps.common.datetimeproxy as datetimeproxy


# Modest default size: recognizable text overlay, low render cost.
FRAME_WIDTH = 320
FRAME_HEIGHT = 240


def render_placeholder_image(
        text_lines   : List[str],
        image_format : str         = 'JPEG',
        size         : Tuple[int, int] = ( FRAME_WIDTH, FRAME_HEIGHT ),
        bg_color     : Tuple[int, int, int] = ( 230, 240, 250 ),
        fg_color     : Tuple[int, int, int] = ( 30, 40, 80 ),
) -> bytes:
    """Pillow-rendered placeholder image. Default bitmap font so
    callers stay independent of system font availability."""
    image = Image.new( mode = 'RGB', size = size, color = bg_color )
    draw = ImageDraw.Draw( image )
    y = 30
    for line in text_lines:
        draw.text( ( 20, y ), line, fill = fg_color )
        y += 24
    buffer = io.BytesIO()
    image.save( buffer, format = image_format )
    return buffer.getvalue()


def render_placeholder_pdf( text_lines : List[str] ) -> bytes:
    """Hand-rolled minimal single-page PDF. Avoids pulling in an
    external PDF library for what amounts to four objects of
    placeholder content. The first line is drawn near the top of the
    page; remaining lines stack below."""
    safe_lines = []
    for line in text_lines:
        text_safe = (
            str( line )
            .replace( '\\', '\\\\' )
            .replace( '(', '\\(' )
            .replace( ')', '\\)' )
        )
        safe_lines.append( text_safe )

    # Build the content stream as one text block with a leading
    # absolute placement followed by line-relative offsets for each
    # additional line. Skip the leading offset for the first line.
    content_parts = [ b'BT /F1 18 Tf 60 740 Td' ]
    for index, text_safe in enumerate( safe_lines ):
        if index > 0:
            content_parts.append( b'0 -24 Td' )
        content_parts.append( f'({text_safe}) Tj'.encode( 'latin-1' ) )
    content_parts.append( b'ET' )
    content_stream = b' '.join( content_parts )

    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        (
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            b'/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>'
        ),
        b'<< /Length ' + str( len( content_stream ) ).encode( 'latin-1' )
        + b' >>\nstream\n' + content_stream + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]

    output = bytearray( b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n' )
    offsets = []
    for index, body in enumerate( objects, start = 1 ):
        offsets.append( len( output ) )
        output += f'{index} 0 obj\n'.encode( 'latin-1' )
        output += body
        output += b'\nendobj\n'

    xref_offset = len( output )
    output += f'xref\n0 {len(objects) + 1}\n'.encode( 'latin-1' )
    output += b'0000000000 65535 f \n'
    for offset in offsets:
        output += f'{offset:010d} 00000 n \n'.encode( 'latin-1' )
    output += (
        f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
        f'startxref\n{xref_offset}\n%%EOF\n'
    ).encode( 'latin-1' )
    return bytes( output )


def render_jpeg_frame(
        text_lines         : List[str],
        timestamp_override : Optional[datetime] = None,
) -> bytes:
    """Pillow-rendered single JPEG frame for camera-style media. The
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
