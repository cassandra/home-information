from django.db import models

from hi.apps.entity.models import Entity
from hi.apps.location.models import Location, LocationView, SvgPositionModel

from .enums import CollectionType


class Collection( models.Model ):
    
    name = models.CharField(
        'Name',
        max_length = 64
    )
    collection_type_str = models.CharField(
        'Collection Type',
        max_length = 32,
        null = False, blank = False,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Collection'
        verbose_name_plural = 'Collections'

    @property
    def collection_type(self):
        return CollectionType.from_name_safe( self.collection_type_str )

    @collection_type.setter
    def collection_type( self, collection_type : CollectionType ):
        self.collection_type_str = str(collection_type)
        return
        
    
class CollectionEntity(models.Model):

    collection = models.ForeignKey(
        Collection,
        related_name = 'entities',
        verbose_name = 'Collection',
        on_delete=models.CASCADE,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'collections',
        verbose_name = 'Entity',
        on_delete=models.CASCADE,
    )
    order_id = models.PositiveIntegerField(
        'Order Id',
        default = 0,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        ordering = [ 'order_id' ]
        indexes = [
            models.Index( fields=[ 'collection', 'entity' ] ),
        ]

        
class CollectionPosition( SvgPositionModel ):

    location = models.ForeignKey(
        Location,
        related_name = 'collection_positions',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
    )
    collection = models.ForeignKey(
        Collection,
        related_name = 'positions',
        verbose_name = 'Collection',
        on_delete = models.CASCADE,
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

    
class CollectionView(models.Model):
    
    collection = models.ForeignKey(
        Collection,
        related_name = 'location_views',
        verbose_name = 'Collection',
        on_delete = models.CASCADE,
    )
    location_view = models.ForeignKey(
        LocationView,
        related_name = 'collections',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
    )
    order_id = models.PositiveIntegerField(
        'Order Id',
        default = 0,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Collection View'
        verbose_name_plural = 'Collection Views'

