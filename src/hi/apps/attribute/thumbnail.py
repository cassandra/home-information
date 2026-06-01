"""Thumbnail generation for attribute file values + the shared
bytes-to-PNG pipeline.

Three classes:

  - ``ThumbnailHelpers``: the pure bytes-in / bytes-out conversion
    pipeline plus its supporting constants (supported mime types,
    size caps, PDF render config). Reusable by any caller that
    already has bytes in memory (e.g. integration referencers
    fetching upstream original-bytes).

  - ``AttributeThumbnailRules``: attribute-specific rules for
    mime-type resolution (filename fallback) and thumbnail-path
    computation under ``default_storage``.

  - ``AttributeThumbnail``: storage-aware wrapper. Reads the
    attribute's file_value from ``default_storage``, applies an
    existence-skip + pre-read size cap, delegates the conversion
    to ``ThumbnailHelpers``, and writes the PNG back to storage
    at the rule-computed path.
"""
import logging
import mimetypes
from io import BytesIO
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Optional

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

if TYPE_CHECKING:
    from .models import AttributeModel

logger = logging.getLogger(__name__)


class ThumbnailHelpers:
    """Pure bytes-to-PNG thumbnail pipeline + the constants that
    parameterize it. All members are class-level; nothing here
    needs per-instance state."""

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

    # Per-mime-type input size caps. PDFs get a tighter ceiling
    # because rendering cost scales with page dimensions and
    # complexity, not raw byte count -- a small but pathological PDF
    # can still be much more expensive than a moderately sized image.
    MAX_SOURCE_BYTES = 20 * 1024 * 1024
    MAX_PDF_SOURCE_BYTES = 10 * 1024 * 1024

    # Bounds on PDF rendering. PDF_RENDER_SIZE caps the rasterized
    # output dimensions before the thumbnail resize, preventing a
    # large-page PDF from producing a multi-GB pixel buffer at
    # pdf2image's 200-DPI default. PDF_RENDER_TIMEOUT_SECS is
    # threaded through to the underlying pdftoppm subprocess so a
    # crafted PDF can't hang generation indefinitely.
    PDF_RENDER_SIZE = (640, 640)
    PDF_RENDER_TIMEOUT_SECS = 30

    @classmethod
    def max_bytes_for_mime(cls, mime_type : str) -> int:
        if mime_type in cls.THUMBNAIL_PDF_MIME_TYPES:
            return cls.MAX_PDF_SOURCE_BYTES
        return cls.MAX_SOURCE_BYTES

    @classmethod
    def bytes_to_thumbnail_png(
            cls, source_bytes : bytes, mime_type : str,
    ) -> Optional[bytes]:
        """Convert source bytes + mime_type into a PNG thumbnail.
        Returns None on any failure (unsupported mime, oversize
        input, malformed bytes, missing optional dependency).
        Best-effort: callers should treat None as "no thumbnail"
        rather than as an error to surface."""
        if not source_bytes:
            return None

        mime_lower = ( mime_type or '' ).split( ';', 1 )[0].strip().lower()
        if mime_lower not in cls.THUMBNAIL_SUPPORTED_MIME_TYPES:
            return None

        max_bytes = cls.max_bytes_for_mime( mime_lower )
        if len( source_bytes ) > max_bytes:
            logger.info(
                f'Thumbnail skipped: source too large '
                f'({len(source_bytes)} bytes, limit {max_bytes} '
                f'for {mime_lower}).'
            )
            return None

        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
        except Exception as e:
            logger.warning(
                f'Pillow unavailable for thumbnail generation: {e}'
            )
            return None

        try:
            if mime_lower in cls.THUMBNAIL_PDF_MIME_TYPES:
                source_img = cls._render_pdf_first_page( source_bytes )
                if source_img is None:
                    return None
            else:
                with Image.open( BytesIO( source_bytes ) ) as opened:
                    source_img = ImageOps.exif_transpose( opened ).copy()

            resampling = (
                Image.Resampling.LANCZOS
                if hasattr( Image, 'Resampling' )
                else Image.LANCZOS
            )
            source_img.thumbnail( cls.THUMBNAIL_SIZE, resampling )

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
                'Thumbnail skipped: unrecognized image content.'
            )
        except Exception as e:
            logger.warning( f'Thumbnail generation failed: {e}' )
        return None

    @classmethod
    def _render_pdf_first_page(cls, pdf_bytes : bytes):
        """Rasterize the first page of a PDF to a PIL Image.
        Returns None when pdf2image is unavailable or rendering
        fails."""
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
                size = cls.PDF_RENDER_SIZE,
                timeout = cls.PDF_RENDER_TIMEOUT_SECS,
            )
            if not pages:
                return None
            return pages[0]
        except Exception as e:
            logger.warning( f'Error rendering PDF thumbnail: {e}' )
            return None


class AttributeThumbnailRules:

    THUMBNAIL_SUBDIRECTORY = 'thumbnails'
    THUMBNAIL_SUFFIX = '.thumb.png'

    @classmethod
    def effective_file_mime_type(cls, file_value, file_mime_type):
        if file_mime_type:
            mime_type = file_mime_type.split(';', 1)[0].strip().lower()
            if mime_type:
                return mime_type

        if file_value and file_value.name:
            guessed_mime_type, _ = mimetypes.guess_type(file_value.name)
            if guessed_mime_type:
                return guessed_mime_type.strip().lower()
        return None

    @classmethod
    def supports_thumbnail_generation(cls, file_value, file_mime_type):
        if not file_value or not file_value.name:
            return False

        mime_type = cls.effective_file_mime_type(
            file_value=file_value,
            file_mime_type=file_mime_type,
        )
        return bool(
            mime_type
            and mime_type in ThumbnailHelpers.THUMBNAIL_SUPPORTED_MIME_TYPES
        )

    @classmethod
    def thumbnail_relative_path(cls, file_value, file_mime_type):
        if not cls.supports_thumbnail_generation(
                file_value = file_value, file_mime_type = file_mime_type,
        ):
            return None

        source_path = PurePosixPath(file_value.name)
        thumbnail_name = f'{source_path.stem}{cls.THUMBNAIL_SUFFIX}'
        if str(source_path.parent) == '.':
            return str(
                PurePosixPath(cls.THUMBNAIL_SUBDIRECTORY) / thumbnail_name
            )
        return str(
            source_path.parent / cls.THUMBNAIL_SUBDIRECTORY / thumbnail_name
        )


class AttributeThumbnail:

    def __init__(self, attribute: 'AttributeModel'):
        self.attribute = attribute

    def generate_thumbnail_best_effort(self, force=False):
        thumbnail_path = self.attribute.thumbnail_relative_path
        if not thumbnail_path:
            return False

        if not force and default_storage.exists(thumbnail_path):
            return True

        mime_type = AttributeThumbnailRules.effective_file_mime_type(
            file_value=self.attribute.file_value,
            file_mime_type=self.attribute.file_mime_type,
        )

        # Pre-read size check: skip without reading the file from
        # storage when we already know we'd reject the bytes. The
        # shared converter re-checks against the same limit on the
        # bytes it actually sees; this guard is just an I/O save.
        file_value = self.attribute.file_value
        file_size = getattr( file_value, 'size', None ) if file_value else None
        if file_size is not None:
            max_bytes = ThumbnailHelpers.max_bytes_for_mime( mime_type )
            if file_size > max_bytes:
                logger.info(
                    f'Skipping thumbnail generation for {file_value.name}: '
                    f'file too large ({file_size} bytes, '
                    f'limit {max_bytes} bytes for {mime_type})'
                )
                return False

        try:
            with default_storage.open(file_value.name, 'rb') as file_handle:
                source_bytes = file_handle.read()
        except Exception as e:
            logger.warning(
                f'Error reading source for thumbnail '
                f'{file_value.name}: {e}'
            )
            return False

        png_bytes = ThumbnailHelpers.bytes_to_thumbnail_png(
            source_bytes = source_bytes, mime_type = mime_type,
        )
        if png_bytes is None:
            return False

        if default_storage.exists(thumbnail_path):
            default_storage.delete(thumbnail_path)
        default_storage.save(thumbnail_path, ContentFile(png_bytes))
        return True
