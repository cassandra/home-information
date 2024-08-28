from django.db import models

from .enums import ViewType


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
    svg_viewbox = models.CharField(
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


class LocationView(models.Model):

    location = models.ForeignKey(
        Location,
        related_name = 'views',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
        null = False, blank = False,
    )
    view_type_str = models.CharField(
        'View Type',
        max_length = 32,
        null = False, blank = False,
    )
    name = models.CharField(
        'Name',
        max_length = 64,
        null = False, blank = False,
    )
    svg_viewbox = models.CharField(
        'Viewbox',
        max_length = 64,
        null = False, blank = False,
    )

    svg_rotation = models.DecimalField(
        'Rotation',
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
    def view_type(self):
        return ViewType.from_name_safe( self.view_type_str )

    @view_type.setter
    def view_type( self, view_type : ViewType ):
        self.view_type_str = str(view_type)
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
    svg_rotation = models.DecimalField(
        'Rotation',
        max_digits = 12,
        decimal_places = 6,
        default = 0.0,
    )
    

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
