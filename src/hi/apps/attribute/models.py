import json
import logging
import mimetypes
from io import BytesIO
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models

from hi.apps.attribute.value_ranges import PredefinedValueRanges
from hi.apps.common.file_utils import generate_unique_filename

from hi.integrations.transient_models import IntegrationKey

from .enums import (
    AttributeValueType,
    AttributeType,
)
from .managers import ActiveAttributeManager, DeletedAttributeManager

logger = logging.getLogger(__name__)


class AttributeModel(models.Model):

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

    supports_soft_delete = False

    class Meta:
        abstract = True
        ordering = ['order_id', 'id']
 
    name = models.CharField(
        'Name',
        max_length = 64,
    )
    value = models.TextField(
        'Value',
        blank = True, null = True,
    )
    file_value = models.FileField(
        upload_to = 'attributes/',  # Subclasses override via get_upload_to()
        blank = True, null = True,
    )
    file_mime_type = models.CharField(
        'Mime Type',
        max_length = 128,
        null = True, blank = True,
    )
    value_type_str = models.CharField(
        'Value Type',
        max_length = 32,
        null = False, blank = False,
    )
    value_range_str = models.TextField(
        'Value Range',
        null = True, blank = True,
    )
    integration_key_str = models.CharField(
        'Integration Key',
        max_length = 128,
        null = True, blank = True,
    )
    attribute_type_str = models.CharField(
        'Attribute Type',
        max_length = 32,
        null = False, blank = False,
    )
    is_editable = models.BooleanField(
        'Editable?',
        default = True,
    )
    is_required = models.BooleanField(
        'Required?',
        default = False,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )
    updated_datetime = models.DateTimeField(
        'Updated',
        auto_now=True,
        blank = True,
    )
    order_id = models.PositiveIntegerField(
        'Ordering Index',
        default = 0,
    )

    def get_upload_to(self):
        raise NotImplementedError('Subclasses should override this method.' )
    
    def get_attribute_default_value(self):
        return None

    @property
    def display_description( self ):
        return None

    def __str__(self):
        return f'Attr: {self.name}={self.value} [{self.value_type_str}] [{self.attribute_type_str}]'
    
    def __repr__(self):
        return self.__str__()
    
    @property
    def value_type(self) -> AttributeValueType:
        return AttributeValueType.from_name_safe( self.value_type_str )

    @value_type.setter
    def value_type( self, value_type : AttributeValueType ):
        self.value_type_str = str(value_type)
        return

    @property
    def integration_key(self) -> IntegrationKey:
        if not self.integration_key_str:
            return None
        return IntegrationKey.from_string( self.integration_key_str )

    @integration_key.setter
    def integration_key( self, integration_key : IntegrationKey ):
        if integration_key:
            self.integration_key_str = str(integration_key)
        else:
            self.integration_key_str = None
        return

    @property
    def attribute_type(self) -> AttributeType:
        return AttributeType.from_name_safe( self.attribute_type_str )

    @attribute_type.setter
    def attribute_type( self, attribute_type : AttributeType ):
        self.attribute_type_str = str(attribute_type)
        return

    @property
    def is_predefined(self):
        return bool( self.attribute_type == AttributeType.PREDEFINED )
    
    def choices(self):
        # First check predefined ids
        choice_list = PredefinedValueRanges.get_choices( self.value_range_str )
        if choice_list:
            return choice_list
        if not self.value_range_str:
            return list()
        try:
            value_range = json.loads( self.value_range_str )
            if isinstance( value_range, dict ):
                return [ ( k, v ) for k, v in value_range.items() ]
            if isinstance( value_range, list ):
                return [ ( x, x ) for x in value_range ]
        except json.JSONDecodeError as e:
            logger.error( f'Bad value range for attribute {self.name}: {e}' )
            pass
        return dict()

    def _effective_file_mime_type(self):
        if self.file_mime_type:
            mime_type = self.file_mime_type.split(';', 1)[0].strip().lower()
            if mime_type:
                return mime_type

        if self.file_value and self.file_value.name:
            guessed_mime_type, _ = mimetypes.guess_type(self.file_value.name)
            if guessed_mime_type:
                return guessed_mime_type.strip().lower()
        return None

    @property
    def supports_thumbnail_generation(self):
        if not self.file_value or not self.file_value.name:
            return False

        mime_type = self._effective_file_mime_type()
        if not mime_type:
            return False
        return bool(mime_type in self.THUMBNAIL_SUPPORTED_MIME_TYPES)

    @property
    def thumbnail_relative_path(self):
        if not self.supports_thumbnail_generation:
            return None

        source_path = PurePosixPath(self.file_value.name)
        thumbnail_name = f'{source_path.stem}{self.THUMBNAIL_SUFFIX}'
        if str(source_path.parent) == '.':
            return str(PurePosixPath(self.THUMBNAIL_SUBDIRECTORY) / thumbnail_name)
        return str(source_path.parent / self.THUMBNAIL_SUBDIRECTORY / thumbnail_name)

    def _thumbnail_exists(self):
        if hasattr(self, '_thumbnail_exists_cache'):
            return self._thumbnail_exists_cache

        thumbnail_path = self.thumbnail_relative_path
        self._thumbnail_exists_cache = bool(
            thumbnail_path and default_storage.exists(thumbnail_path)
        )
        return self._thumbnail_exists_cache

    @property
    def has_thumbnail(self):
        return self._thumbnail_exists()

    @property
    def thumbnail_url(self):
        if not self._thumbnail_exists():
            return None
        return default_storage.url(self.thumbnail_relative_path)

    @property
    def preview_state(self):
        if self.has_thumbnail:
            return 'thumbnail'
        return 'placeholder'

    def _render_pdf_first_page_image(self, file_handle, image_module):
        try:
            from pdf2image import convert_from_bytes
        except Exception as e:
            logger.warning( f'pdf2image unavailable for PDF thumbnail generation: {e}' )
            return None

        try:
            pdf_bytes = file_handle.read()
            rendered_pages = convert_from_bytes(
                pdf_bytes,
                first_page=1,
                last_page=1,
            )
            if not rendered_pages:
                logger.warning( f'Cannot generate thumbnail for empty PDF: {self.file_value.name}' )
                return None
            return rendered_pages[0]

        except Exception as e:
            logger.warning( f'Error rendering PDF thumbnail for {self.file_value.name}: {e}' )
            return None

    def _load_source_image_for_thumbnail(self, file_handle, mime_type, image_module, image_ops_module):
        if mime_type in self.THUMBNAIL_PDF_MIME_TYPES:
            return self._render_pdf_first_page_image(file_handle, image_module)

        with image_module.open(file_handle) as img:
            processed_img = image_ops_module.exif_transpose(img)
            return processed_img.copy()

    def generate_thumbnail_best_effort(self, force=False):
        thumbnail_path = self.thumbnail_relative_path
        if not thumbnail_path:
            return False

        mime_type = self._effective_file_mime_type()

        if not force and default_storage.exists(thumbnail_path):
            self._thumbnail_exists_cache = True
            return True

        if self.file_value and getattr(self.file_value, 'size', None):
            if self.file_value.size > self.THUMBNAIL_MAX_SOURCE_BYTES:
                logger.info(
                    f'Skipping thumbnail generation for {self.file_value.name}: '
                    f'file too large ({self.file_value.size} bytes)'
                )
                return False

        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
        except Exception as e:
            logger.warning(f'Pillow unavailable for thumbnail generation: {e}')
            return False

        try:
            with default_storage.open(self.file_value.name, 'rb') as file_handle:
                processed_img = self._load_source_image_for_thumbnail(
                    file_handle=file_handle,
                    mime_type=mime_type,
                    image_module=Image,
                    image_ops_module=ImageOps,
                )

            if not processed_img:
                self._thumbnail_exists_cache = False
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
            self._thumbnail_exists_cache = True
            return True

        except UnidentifiedImageError:
            logger.warning(
                f'Cannot generate thumbnail due to unrecognized image content: {self.file_value.name}'
            )
        except Exception as e:
            logger.warning(
                f'Error generating thumbnail for {self.file_value.name}: {e}'
            )
        self._thumbnail_exists_cache = False
        return False

    def save(self, *args, **kwargs):
        # Skip history tracking for kwargs that disable it
        track_history = kwargs.pop('track_history', True)
        
        if self.file_value and self.file_value.name:
            self.file_value.field.upload_to = self.get_upload_to()
            if not self.value:
                self.value = self.file_value.name
            all_manager = getattr( self.__class__, 'all_objects', self.__class__.objects )
            if not self.pk or not all_manager.filter( pk = self.pk ).exists():
                self.file_value.name = generate_unique_filename( self.file_value.name )
        
        # Save the attribute first
        super().save(*args, **kwargs)
        
        # Track history for value-based attributes only AFTER saving
        if track_history and not self.value_type.is_file:
            self._create_history_record()
        
        return
    
    def _create_history_record(self):
        """Create a history record for this attribute's value change."""
        # Get the history model class for this concrete attribute type
        history_model_class = self._get_history_model_class()
        if not history_model_class:
            return
        
        # Create history record
        history_model_class.objects.create(
            attribute=self,
            value=self.value
        )

    def _get_history_model_class(self):
        """
        Get the corresponding history model class for this attribute type.
        Must be implemented by all concrete subclasses.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _get_history_model_class() "
            "to provide history tracking support."
        )
    
    def delete( self, *args, **kwargs ):
        """ Deleting file from MEDIA_ROOT on best effort basis.  Ignore if fails. """
        
        thumbnail_path = self.thumbnail_relative_path

        if self.file_value:
            try:
                if default_storage.exists( self.file_value.name ):
                    default_storage.delete( self.file_value.name )
                    logger.debug( f'Deleted Attribute file: {self.file_value.name}' )
                else:
                    logger.warn( f'Attribute file not found: {self.file_value.name}' )
            except Exception as e:
                # Log the error or handle it accordingly
                logger.warn( f'Error deleting Attribute file {self.file_value.name}: {e}' )

        if thumbnail_path:
            try:
                if default_storage.exists(thumbnail_path):
                    default_storage.delete(thumbnail_path)
                    logger.debug(f'Deleted Attribute thumbnail: {thumbnail_path}')
            except Exception as e:
                logger.warn(f'Error deleting Attribute thumbnail {thumbnail_path}: {e}')

        super().delete( *args, **kwargs )
        return


class SoftDeleteAttributeModel(AttributeModel):
    """Base class for attribute models that support soft delete."""

    supports_soft_delete = True

    is_deleted = models.BooleanField(
        'Deleted?',
        default = False,
        db_index = True,
    )

    objects = ActiveAttributeManager()
    all_objects = models.Manager()
    deleted_objects = DeletedAttributeManager()

    class Meta(AttributeModel.Meta):
        abstract = True

    def soft_delete( self ):
        self.is_deleted = True
        self.save(
            update_fields = ['is_deleted', 'updated_datetime'],
            track_history = False,
        )

    def restore_from_deleted( self ):
        self.is_deleted = False
        self.save(
            update_fields = ['is_deleted', 'updated_datetime'],
            track_history = False,
        )

    def delete( self, *args, **kwargs ):
        hard_delete = kwargs.pop( 'hard_delete', False )
        if hard_delete:
            return super().delete(*args, **kwargs)
        self.soft_delete()
        return (1, {self.__class__.__name__: 1})
    
    
class AttributeValueHistoryModel(models.Model):
    """
    Abstract base class for tracking attribute value changes.
    Each concrete attribute subclass should have its own history model
    that defines the foreign key to its specific attribute type.
    
    Only tracks value-based attributes (Text, Boolean, Integer, Float, etc.).
    File attributes are excluded and will be handled separately.
    """
    
    class Meta:
        abstract = True
        ordering = ['-changed_datetime']
    
    value = models.TextField(
        'Value',
        blank=True, null=True,
    )
    changed_datetime = models.DateTimeField(
        'Changed',
        auto_now_add=True,
        db_index=True,
    )

    def __str__(self):
        return f'Changed at {self.changed_datetime}'
