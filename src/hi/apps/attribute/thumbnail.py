import logging
import mimetypes
from io import BytesIO
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

if TYPE_CHECKING:
    from .models import AttributeModel

logger = logging.getLogger(__name__)


class AttributeThumbnailRules:

    THUMBNAIL_SUBDIRECTORY = 'thumbnails'
    THUMBNAIL_SUFFIX = '.thumb.png'
    THUMBNAIL_IMAGE_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/gif',
    }
    THUMBNAIL_PDF_MIME_TYPES = {
        'application/pdf',
    }
    THUMBNAIL_SUPPORTED_MIME_TYPES = THUMBNAIL_IMAGE_MIME_TYPES | THUMBNAIL_PDF_MIME_TYPES

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
        return bool(mime_type and mime_type in cls.THUMBNAIL_SUPPORTED_MIME_TYPES)

    @classmethod
    def thumbnail_relative_path(cls, file_value, file_mime_type):
        if not cls.supports_thumbnail_generation( file_value = file_value, file_mime_type = file_mime_type ):
            return None

        source_path = PurePosixPath(file_value.name)
        thumbnail_name = f'{source_path.stem}{cls.THUMBNAIL_SUFFIX}'
        if str(source_path.parent) == '.':
            return str(PurePosixPath(cls.THUMBNAIL_SUBDIRECTORY) / thumbnail_name)
        return str(source_path.parent / cls.THUMBNAIL_SUBDIRECTORY / thumbnail_name)


class AttributeThumbnail:

    THUMBNAIL_SIZE = (320, 320)

    # Per-mime-type input size caps. PDFs get a tighter ceiling because
    # rendering cost scales with page dimensions and complexity, not
    # raw byte count — a small but pathological PDF can still be much
    # more expensive than a moderately sized image.
    THUMBNAIL_MAX_SOURCE_BYTES = 20 * 1024 * 1024
    THUMBNAIL_MAX_PDF_SOURCE_BYTES = 10 * 1024 * 1024

    # Bounds on PDF rendering. ``PDF_RENDER_SIZE`` caps the rasterized
    # output dimensions before the thumbnail resize, preventing a
    # large-page PDF from producing a multi-GB pixel buffer at
    # pdf2image's 200-DPI default. ``PDF_RENDER_TIMEOUT_SECS`` is
    # threaded through to the underlying pdftoppm subprocess so a
    # crafted PDF can't hang generation indefinitely.
    PDF_RENDER_SIZE = (640, 640)
    PDF_RENDER_TIMEOUT_SECS = 30

    def __init__(self, attribute: 'AttributeModel'):
        self.attribute = attribute

    def _max_source_bytes_for_mime_type(self, mime_type):
        if mime_type in AttributeThumbnailRules.THUMBNAIL_PDF_MIME_TYPES:
            return self.THUMBNAIL_MAX_PDF_SOURCE_BYTES
        return self.THUMBNAIL_MAX_SOURCE_BYTES

    def _render_pdf_first_page_image(self, file_handle):
        try:
            from pdf2image import convert_from_bytes
        except Exception as e:
            logger.warning( f'pdf2image unavailable for PDF thumbnail generation: {e}' )
            return None

        try:
            pdf_bytes = file_handle.read()
            rendered_pages = convert_from_bytes(
                pdf_bytes,
                first_page = 1,
                last_page = 1,
                size = self.PDF_RENDER_SIZE,
                timeout = self.PDF_RENDER_TIMEOUT_SECS,
            )
            if not rendered_pages:
                logger.warning( f'Cannot generate thumbnail for empty PDF: {self.attribute.file_value.name}' )
                return None
            return rendered_pages[0]

        except Exception as e:
            logger.warning( f'Error rendering PDF thumbnail for {self.attribute.file_value.name}: {e}' )
            return None

    def _load_source_image_for_thumbnail(self, file_handle, mime_type, image_module, image_ops_module):
        if mime_type in AttributeThumbnailRules.THUMBNAIL_PDF_MIME_TYPES:
            return self._render_pdf_first_page_image(file_handle=file_handle)

        with image_module.open(file_handle) as img:
            processed_img = image_ops_module.exif_transpose(img)
            return processed_img.copy()

    def generate_thumbnail_best_effort(self, force=False):
        thumbnail_path = self.attribute.thumbnail_relative_path
        if not thumbnail_path:
            return False

        mime_type = AttributeThumbnailRules.effective_file_mime_type(
            file_value=self.attribute.file_value,
            file_mime_type=self.attribute.file_mime_type,
        )

        if not force and default_storage.exists(thumbnail_path):
            return True

        if self.attribute.file_value and getattr(self.attribute.file_value, 'size', None):
            max_source_bytes = self._max_source_bytes_for_mime_type( mime_type )
            if self.attribute.file_value.size > max_source_bytes:
                logger.info(
                    f'Skipping thumbnail generation for {self.attribute.file_value.name}: '
                    f'file too large ({self.attribute.file_value.size} bytes, '
                    f'limit {max_source_bytes} bytes for {mime_type})'
                )
                return False

        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
        except Exception as e:
            logger.warning( f'Pillow unavailable for thumbnail generation: {e}' )
            return False

        try:
            with default_storage.open(self.attribute.file_value.name, 'rb') as file_handle:
                processed_img = self._load_source_image_for_thumbnail(
                    file_handle=file_handle,
                    mime_type=mime_type,
                    image_module=Image,
                    image_ops_module=ImageOps,
                )

            if not processed_img:
                return False

            resampling = (
                Image.Resampling.LANCZOS
                if hasattr(Image, 'Resampling')
                else Image.LANCZOS
            )
            processed_img.thumbnail(self.THUMBNAIL_SIZE, resampling)

            if processed_img.mode not in ('RGB', 'RGBA'):
                if 'A' in processed_img.getbands():
                    processed_img = processed_img.convert('RGBA')
                else:
                    processed_img = processed_img.convert('RGB')

            bytes_buffer = BytesIO()
            processed_img.save(bytes_buffer, format='PNG', optimize=True)
            thumbnail_content = ContentFile(bytes_buffer.getvalue())

            if default_storage.exists(thumbnail_path):
                default_storage.delete(thumbnail_path)

            default_storage.save(thumbnail_path, thumbnail_content)
            return True
        except UnidentifiedImageError:
            logger.warning( f'Cannot generate thumbnail due to unrecognized image content: {self.attribute.file_value.name}' )
        except Exception as e:
            logger.warning( f'Error generating thumbnail for {self.attribute.file_value.name}: {e}' )
        return False
