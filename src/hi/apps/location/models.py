import logging

from django.core.files.storage import default_storage
from django.db import models

from hi.apps.common.svg_models import SvgDecimalField, SvgViewBox
from hi.apps.attribute.models import AttributeModel
from hi.enums import ItemType
from hi.models import ItemTypeModelMixin

from .enums import LocationViewType

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
    order_id = models.PositiveIntegerField(
        'Order Id',
        default = 0,
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
