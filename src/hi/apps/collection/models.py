from django.db import models

from hi.apps.entity.models import Entity
from hi.apps.location.models import (
    Location,
    LocationItemModelMixin,
    LocationItemPositionModel,
    LocationItemPathModel,
    LocationView,
)
from hi.enums import ItemType

from .enums import CollectionType, CollectionViewType


class Collection( models.Model, LocationItemModelMixin ):
    
    name = models.CharField(
        'Name',
        max_length = 64
    )
    collection_type_str = models.CharField(
        'Collection Type',
        max_length = 32,
        null = False, blank = False,
    )
    collection_view_type_str = models.CharField(
        'View Type',
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

    class Meta:
        verbose_name = 'Collection'
        verbose_name_plural = 'Collections'
        ordering = [ 'order_id' ]

    @property
    def item_type(self) -> ItemType:
        return ItemType.COLLECTION
    
    @property
    def collection_type(self):
        return CollectionType.from_name_safe( self.collection_type_str )

    @collection_type.setter
    def collection_type( self, collection_type : CollectionType ):
        self.collection_type_str = str(collection_type)
        return
    
    @property
    def collection_view_type(self):
        return CollectionViewType.from_name_safe( self.collection_view_type_str )

    @collection_view_type.setter
    def collection_view_type( self, collection_view_type : CollectionViewType ):
        self.collection_view_type_str = str(collection_view_type)
        return
        
    
class CollectionEntity(models.Model):

    collection = models.ForeignKey(
        Collection,
        related_name = 'entities',
        verbose_name = 'Collection',
        on_delete = models.CASCADE,
    )
    entity = models.ForeignKey(
        Entity,
        related_name = 'collections',
        verbose_name = 'Entity',
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
        verbose_name = 'Collection Entity'
        verbose_name_plural = 'Collection Entities'
        ordering = [ 'order_id' ]
        indexes = [
            models.Index( fields=[ 'collection', 'entity' ] ),
        ]

        
class CollectionPosition( LocationItemPositionModel ):

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

    class Meta:
        verbose_name = 'Collection Position'
        verbose_name_plural = 'Collection Positions'
        constraints = [
            models.UniqueConstraint(
                fields = [ 'location', 'collection' ],
                name = 'collection_position_location_entity',
            ),
        ]
            
    @property
    def location_item(self) -> LocationItemModelMixin:
        return self.collection
    
    
class CollectionPath( LocationItemPathModel ):
    """
    - For collection represented by an arbitary (usually closed) SVG path.
    - The styling of the path is determined by the CollectionType. 
    - An Collection is not required to have an CollectionPath.  
    """
    
    location = models.ForeignKey(
        Location,
        related_name = 'collection_paths',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
    )
    collection = models.ForeignKey(
        Collection,
        related_name = 'paths',
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

    class Meta:
        verbose_name = 'Collection Path'
        verbose_name_plural = 'Collection Paths'
        constraints = [
            models.UniqueConstraint(
                fields = [ 'location', 'collection' ],
                name = 'collection_path_location_collection', ),
        ]
            
    @property
    def location_item(self) -> LocationItemModelMixin:
        return self.collection

    
class CollectionView(models.Model):
    
    collection = models.ForeignKey(
        Collection,
        related_name = 'collection_views',
        verbose_name = 'Collection',
        on_delete = models.CASCADE,
    )
    location_view = models.ForeignKey(
        LocationView,
        related_name = 'collection_views',
        verbose_name = 'Location',
        on_delete = models.CASCADE,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Collection View'
        verbose_name_plural = 'Collection Views'

