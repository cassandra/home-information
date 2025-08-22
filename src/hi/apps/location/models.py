import logging

from django.core.files.storage import default_storage
from django.db import models

from hi.apps.common.svg_models import SvgDecimalField, SvgItemPositionBounds, SvgViewBox
from hi.apps.attribute.models import AttributeModel, AttributeValueHistoryModel
from hi.enums import ItemType
from hi.models import ItemTypeModelMixin

from .enums import LocationViewType, SvgStyleName

logger = logging.getLogger(__name__)


class Location( models.Model, ItemTypeModelMixin ):
    
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    svg_fragment_filename = models.CharField(
        'SVG Filename',
        max_length = 255,
        null = False, blank = False,
    )
    svg_view_box_str = models.CharField(
        'Viewbox',
        max_length = 128,
        null = False, blank = False,
    )
    order_id = models.PositiveIntegerField(
        'Order Id',
        default = 0,
        db_index = True,
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
    
    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = [ 'order_id' ]

    def __str__(self):
        return f'{self.name} ({self.id})'

    def __repr__(self):
        return self.__str__()
    
    @property
    def item_type(self) -> ItemType:
        return ItemType.LOCATION

    @property
    def svg_view_box(self):
        return SvgViewBox.from_attribute_value( self.svg_view_box_str )

    @svg_view_box.setter
    def svg_view_box( self, svg_view_box : SvgViewBox ):
        self.svg_view_box_str = str(svg_view_box)
        return

    @property
    def svg_position_bounds( self ):
        svg_view_box = self.svg_view_box
        return SvgItemPositionBounds(
            min_x = svg_view_box.x,
            min_y = svg_view_box.y,
            max_x = svg_view_box.x + svg_view_box.width,
            max_y = svg_view_box.y + svg_view_box.height,
            min_scale = 0.1,
            max_scale = 25.0,
        )
    
    def delete( self, *args, **kwargs ):
        """ Deleting SVG file from MEDIA_ROOT on best effort basis.  Ignore if fails. """
        
        if self.svg_fragment_filename:
            try:
                if default_storage.exists( self.svg_fragment_filename ):
                    default_storage.delete( self.svg_fragment_filename )
                    logger.debug( f'Deleted SVG file: {self.svg_fragment_filename}' )
                else:
                    logger.warn( f'SVG file not found: {self.svg_fragment_filename}' )
            except Exception as e:
                # Log the error or handle it accordingly
                logger.warn( f'Error deleting file {self.svg_fragment_filename}: {e}' )

        else:
            logger.warn( 'No SVG filename for model deletion.' )

        super().delete( *args, **kwargs )
        return

    
class LocationAttribute( AttributeModel ):
    """
    - Information related to an location, e.g., specs, docs, notes, configs
    - The 'attribute type' is used to help define what information the user might need to provide.
    """
    
    location = models.ForeignKey(
        Location,
        related_name = 'attributes',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
    )

    class Meta:
        verbose_name = 'Attribute'
        verbose_name_plural = 'Attributes'
        indexes = [
            models.Index( fields=[ 'name', 'value' ] ),
        ]

    def get_upload_to(self):
        return 'location/attributes/'
    
    def _get_history_model_class(self):
        """Return the history model class for LocationAttribute."""
        return LocationAttributeHistory
    
    def get_history_url_name(self):
        """Return the URL name for LocationAttribute history view."""
        return 'location_attribute_history'
    
    def get_restore_url_name(self):
        """Return the URL name for LocationAttribute restore view."""
        return 'location_attribute_restore'

    
class LocationView( models.Model, ItemTypeModelMixin ):

    location = models.ForeignKey(
        Location,
        related_name = 'views',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
        null = False, blank = False,
    )
    location_view_type_str = models.CharField(
        'View Type',
        max_length = 32,
        null = False, blank = False,
    )
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    svg_view_box_str = models.CharField(
        'Viewbox',
        max_length = 128,
        null = False, blank = False,
    )
    svg_rotate = SvgDecimalField(
        'Rotate',
    )
    svg_style_name_str = models.CharField(
        'Style',
        max_length = 32,
        null = False, blank = False,
    )
    order_id = models.PositiveIntegerField(
        'Order Id',
        default = 0,
        db_index = True,
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
    
    class Meta:
        verbose_name = 'View'
        verbose_name_plural = 'Views'
        ordering = [ 'order_id' ]

    def __str__(self):
        return f'{self.name} ({self.id})'

    def __repr__(self):
        return self.__str__()

    @property
    def item_type(self) -> ItemType:
        return ItemType.LOCATION_VIEW
    
    @property
    def location_view_type(self):
        return LocationViewType.from_name_safe( self.location_view_type_str )

    @location_view_type.setter
    def location_view_type( self, location_view_type : LocationViewType ):
        self.location_view_type_str = str(location_view_type)
        return
    
    @property
    def svg_view_box(self):
        return SvgViewBox.from_attribute_value( self.svg_view_box_str )

    @svg_view_box.setter
    def svg_view_box( self, svg_view_box : SvgViewBox ):
        self.svg_view_box_str = str(svg_view_box)
        return
    
    @property
    def svg_style_name(self):
        return SvgStyleName.from_name_safe( self.svg_style_name_str )

    @svg_style_name.setter
    def svg_style_name( self, svg_style_name : SvgStyleName ):
        self.svg_style_name_str = str(svg_style_name)
        return


class LocationItemModelMixin( ItemTypeModelMixin ):
    # A Location Item is a model that can be associated with a Location
    # and that can visually appeay in one or more Location Views.  This
    # defined an interface that specific instance need to conform to.
    pass

    
class LocationItemPositionModel( models.Model ):
    """
    For models that have a visual representaion that can be overlayed on
    the Location's SVG as an icon with a center position, rotation and scale.
    """
    
    class Meta:
        abstract = True
        
    svg_x = SvgDecimalField(
        'X',
        max_digits = 12,
        decimal_places = 6,
    )
    svg_y = SvgDecimalField(
        'Y',
        max_digits = 12,
        decimal_places = 6,
    )
    svg_scale = SvgDecimalField(
        'Scale',
        max_digits = 12,
        decimal_places = 6,
        default = 1.0,
    )
    svg_rotate = SvgDecimalField(
        'Rotate',
        max_digits = 12,
        decimal_places = 6,
        default = 0.0,
    )

    @property
    def location_item(self) -> LocationItemModelMixin:
        raise NotImplementedError('Subclasses must implement this method.')

    
class LocationItemPathModel( models.Model ):
    """
    For models that have a visual representaion that can be overlayed on
    the Location's SVG as a general SVG path.
    """
    
    class Meta:
        abstract = True
        
    svg_path = models.TextField(
        'Path',
        null = False, blank = False,
    )

    @property
    def location_item(self) -> LocationItemModelMixin:
        raise NotImplementedError('Subclasses must implement this method.')


class LocationAttributeHistory(AttributeValueHistoryModel):
    """History tracking for LocationAttribute changes."""
    
    attribute = models.ForeignKey(
        LocationAttribute,
        related_name='history',
        verbose_name='Location Attribute',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Location Attribute History'
        verbose_name_plural = 'Location Attribute History'
        indexes = [
            models.Index(fields=['attribute', '-changed_datetime']),
        ]
