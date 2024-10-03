from django.db import models

from hi.apps.common.svg_models import SvgItem, SvgViewBox

from .enums import LocationViewType


class Location(models.Model):
    
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    svg_filename = models.CharField(
        'SVG File',
        max_length = 256,
        null = False, blank = False,
    )
    svg_view_box_str = models.CharField(
        'Viewbox',
        max_length = 64,
        null = False, blank = False,
    )
    latitude = models.DecimalField(
        'Latitude',
        max_digits = 11,
        decimal_places = 8,
    )
    longitude = models.DecimalField(
        'Longitude',
        max_digits = 11,
        decimal_places = 8,
    )
    elevation_feet = models.DecimalField(
        'Elevation (ft)',
        max_digits = 9,
        decimal_places = 3,
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

    def __str__(self):
        return f'{self.name} ({self.id})'

    def __repr__(self):
        return self.__str__()
    
    @property
    def svg_view_box(self):
        return SvgViewBox.from_attribute_value( self.svg_view_box_str )

    @svg_view_box.setter
    def svg_view_box( self, svg_view_box : SvgViewBox ):
        self.svg_view_box_str = str(svg_view_box)
        return


class LocationView(models.Model):

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
        max_length = 64,
        null = False, blank = False,
    )
    svg_rotate = models.DecimalField(
        'Rotate',
        max_digits = 9,
        decimal_places = 6,
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

    def __str__(self):
        return f'{self.name} ({self.id})'

    def __repr__(self):
        return self.__str__()

    @property
    def html_id(self):
        return f'hi-location-view-{self.id}'
    
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

    
class SvgPositionModel(models.Model):
    """
    For models that have a visual representaion that can be overlayed on
    the Location's SVG as an icon with a center position, rotartion and scale.
    """
    
    class Meta:
        abstract = True
        
    svg_x = models.DecimalField(
        'X',
        max_digits = 12,
        decimal_places = 6,
    )
    svg_y = models.DecimalField(
        'Y',
        max_digits = 12,
        decimal_places = 6,
    )
    svg_scale = models.DecimalField(
        'Scale',
        max_digits = 12,
        decimal_places = 6,
        default = 1.0,
    )
    svg_rotate = models.DecimalField(
        'Rotate',
        max_digits = 12,
        decimal_places = 6,
        default = 0.0,
    )

    @property
    def svg_item(self) -> SvgItem:
        raise NotImplementedError('Subclasses must implement this method.')

    
class SvgPathModel(models.Model):
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
