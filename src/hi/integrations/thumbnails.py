"""Framework-side thumbnail generation for external references.

Wraps PIL + pdf2image to convert upstream-fetched bytes into a small
PNG. Best-effort: returns None on any failure (unsupported mime
type, oversized input, malformed bytes, missing optional dep).
Callers (integration attach handlers) attach the row regardless of
whether a thumbnail came back -- linking is the primary user goal.
"""
import logging
from io import BytesIO
from typing import Optional


logger = logging.getLogger(__name__)


THUMBNAIL_SIZE = (320, 320)

THUMBNAIL_IMAGE_MIME_TYPES = frozenset({
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
})
THUMBNAIL_PDF_MIME_TYPES = frozenset({
    'application/pdf',
})
THUMBNAIL_SUPPORTED_MIME_TYPES = (
    THUMBNAIL_IMAGE_MIME_TYPES | THUMBNAIL_PDF_MIME_TYPES
)

# Per-mime-type input size caps. PDFs get a tighter ceiling because
# rendering cost scales with page dimensions and complexity, not
# raw byte count -- a small but pathological PDF can still be much
# more expensive than a moderately sized image.
MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_PDF_SOURCE_BYTES = 10 * 1024 * 1024

# Bounds on PDF rendering. PDF_RENDER_SIZE caps the rasterized output
# dimensions before the thumbnail resize, preventing a large-page PDF
# from producing a multi-GB pixel buffer at pdf2image's 200-DPI
# default. PDF_RENDER_TIMEOUT_SECS is threaded through to the
# underlying pdftoppm subprocess so a crafted PDF can't hang
# generation indefinitely.
PDF_RENDER_SIZE = (640, 640)
PDF_RENDER_TIMEOUT_SECS = 30


def generate( bytes_in : bytes, mime_type : str ) -> Optional[bytes]:
    """Generate a PNG thumbnail from upstream bytes. Returns None
    when generation is not possible: unsupported mime type, oversize
    input, malformed bytes, or a missing optional dependency."""
    if not bytes_in:
        return None

    mime_lower = ( mime_type or '' ).split(';', 1)[0].strip().lower()
    if mime_lower not in THUMBNAIL_SUPPORTED_MIME_TYPES:
        return None

    max_bytes = (
        MAX_PDF_SOURCE_BYTES
        if mime_lower in THUMBNAIL_PDF_MIME_TYPES
        else MAX_SOURCE_BYTES
    )
    if len(bytes_in) > max_bytes:
        logger.info(
            f'External reference thumbnail skipped: source too large '
            f'({len(bytes_in)} bytes, limit {max_bytes} for {mime_lower}).'
        )
        return None

    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except Exception as e:
        logger.warning( f'Pillow unavailable for thumbnail generation: {e}' )
        return None

    try:
        if mime_lower in THUMBNAIL_PDF_MIME_TYPES:
            source_img = _render_pdf_first_page( bytes_in )
            if source_img is None:
                return None
        else:
            with Image.open( BytesIO(bytes_in) ) as opened:
                source_img = ImageOps.exif_transpose( opened ).copy()

        resampling = (
            Image.Resampling.LANCZOS
            if hasattr( Image, 'Resampling' )
            else Image.LANCZOS
        )
        source_img.thumbnail( THUMBNAIL_SIZE, resampling )

        if source_img.mode not in ( 'RGB', 'RGBA' ):
            if 'A' in source_img.getbands():
                source_img = source_img.convert( 'RGBA' )
            else:
                source_img = source_img.convert( 'RGB' )

        out_buffer = BytesIO()
        source_img.save( out_buffer, format = 'PNG', optimize = True )
        return out_buffer.getvalue()
    except UnidentifiedImageError:
        logger.warning(
            'External reference thumbnail skipped: unrecognized image content.'
        )
    except Exception as e:
        logger.warning( f'External reference thumbnail generation failed: {e}' )
    return None


def _render_pdf_first_page( pdf_bytes : bytes ):
    """Rasterize the first page of a PDF to a PIL Image. Returns
    None when pdf2image is unavailable or rendering fails."""
    try:
        from pdf2image import convert_from_bytes
    except Exception as e:
        logger.warning(
            f'pdf2image unavailable for PDF thumbnail generation: {e}'
        )
        return None

    try:
        pages = convert_from_bytes(
            pdf_bytes,
            first_page = 1,
            last_page = 1,
            size = PDF_RENDER_SIZE,
            timeout = PDF_RENDER_TIMEOUT_SECS,
        )
        if not pages:
            return None
        return pages[0]
    except Exception as e:
        logger.warning( f'Error rendering PDF thumbnail: {e}' )
        return None
