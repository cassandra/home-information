from django.db import models

from hi.apps.common.svg_models import SvgIconItem
from hi.apps.entity.models import Entity
from hi.apps.location.models import (
    Location,
    LocationView,
    SvgPositionModel,
)

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
    order_id = models.PositiveIntegerField(
        'Order Id',
        default = 0,
    )
    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
    )

    class Meta:
        verbose_name = 'Collection'
        verbose_name_plural = 'Collections'

    @property
    def html_id(self):
        return f'hi-collection-{self.id}'
    
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
        verbose_name = 'Collection Entity'
        verbose_name_plural = 'Collection Entities'
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
    def svg_icon_item(self) -> SvgIconItem:
        return SvgIconItem(
            html_id = f'hi-collection-{self.collection.id}',
            template_name = self.collection.collection_type.svg_icon_template_name,
            position_x = float( self.svg_x ),
            position_y = float( self.svg_y ),
            bounding_box = self.collection.collection_type.svg_icon_bounding_box,
            rotate = float( self.svg_rotate ),
            scale = float( self.svg_scale ),
        )
    
    
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

