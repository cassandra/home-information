import logging
import mimetypes
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

THUMBNAIL_SUBDIRECTORY = 'thumbnails'
THUMBNAIL_SUFFIX = '.thumb.png'
THUMBNAIL_SIZE = (320, 320)
THUMBNAIL_MAX_SOURCE_BYTES = 20 * 1024 * 1024
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


def effective_file_mime_type(file_value, file_mime_type):
    if file_mime_type:
        mime_type = file_mime_type.split(';', 1)[0].strip().lower()
        if mime_type:
            return mime_type

    if file_value and file_value.name:
        guessed_mime_type, _ = mimetypes.guess_type(file_value.name)
        if guessed_mime_type:
            return guessed_mime_type.strip().lower()
    return None


def _render_pdf_first_page_image(file_handle, file_name):
    try:
        from pdf2image import convert_from_bytes
    except Exception as e:
        logger.warning(f'pdf2image unavailable for PDF thumbnail generation: {e}')
        return None

    try:
        pdf_bytes = file_handle.read()
        rendered_pages = convert_from_bytes(
            pdf_bytes,
            first_page=1,
            last_page=1,
        )
        if not rendered_pages:
            logger.warning(f'Cannot generate thumbnail for empty PDF: {file_name}')
            return None
        return rendered_pages[0]

    except Exception as e:
        logger.warning(f'Error rendering PDF thumbnail for {file_name}: {e}')
        return None


def _load_source_image_for_thumbnail(file_handle, mime_type, image_module, image_ops_module, file_name):
    if mime_type in THUMBNAIL_PDF_MIME_TYPES:
        return _render_pdf_first_page_image(file_handle=file_handle, file_name=file_name)

    with image_module.open(file_handle) as img:
        processed_img = image_ops_module.exif_transpose(img)
        return processed_img.copy()


def generate_thumbnail_best_effort(attribute, force=False):
    thumbnail_path = attribute.thumbnail_relative_path
    if not thumbnail_path:
        return False

    mime_type = effective_file_mime_type(
        file_value=attribute.file_value,
        file_mime_type=attribute.file_mime_type,
    )

    if not force and default_storage.exists(thumbnail_path):
        attribute._thumbnail_exists_cache = True
        return True

    if attribute.file_value and getattr(attribute.file_value, 'size', None):
        if attribute.file_value.size > THUMBNAIL_MAX_SOURCE_BYTES:
            logger.info(
                f'Skipping thumbnail generation for {attribute.file_value.name}: '
                f'file too large ({attribute.file_value.size} bytes)'
            )
            return False

    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except Exception as e:
        logger.warning(f'Pillow unavailable for thumbnail generation: {e}')
        return False

    try:
        with default_storage.open(attribute.file_value.name, 'rb') as file_handle:
            processed_img = _load_source_image_for_thumbnail(
                file_handle=file_handle,
                mime_type=mime_type,
                image_module=Image,
                image_ops_module=ImageOps,
                file_name=attribute.file_value.name,
            )

        if not processed_img:
            attribute._thumbnail_exists_cache = False
            return False

        resampling = (
            Image.Resampling.LANCZOS
            if hasattr(Image, 'Resampling')
            else Image.LANCZOS
        )
        processed_img.thumbnail(THUMBNAIL_SIZE, resampling)

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
        attribute._thumbnail_exists_cache = True
        return True

    except UnidentifiedImageError:
        logger.warning(
            f'Cannot generate thumbnail due to unrecognized image content: {attribute.file_value.name}'
        )
    except Exception as e:
        logger.warning(
            f'Error generating thumbnail for {attribute.file_value.name}: {e}'
        )
    attribute._thumbnail_exists_cache = False
    return False
