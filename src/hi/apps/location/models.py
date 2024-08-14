from django.db import models


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
    order_id = models.IntegerField(
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
        verbose_name = 'View',
        on_delete = models.CASCADE,
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
    order_id = models.IntegerField(
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
    
