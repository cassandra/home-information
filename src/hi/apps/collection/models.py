from django.db import models

from hi.apps.entity.models import Entity

from .enums import CollectionType


class Collection( models.Model ):
    
    name = models.CharField(
        'Name',
        max_length = 64
    )
    entities = models.ManyToManyField(
        Entity,
        through = 'CollectionRelation',
        related_name = 'collections'
        
    )
    collection_type_str = models.CharField(
        'Collection Type',
        max_length = 32,
        null = False, blank = False,
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
        
    
class CollectionRelation(models.Model):

    entity = models.ForeignKey(
        Entity,
        verbose_name = 'Entity',
        on_delete=models.CASCADE,
    )
    collection = models.ForeignKey(
        Collection,
        verbose_name = 'Collection',
        on_delete=models.CASCADE,
    )
    order_id = models.PositiveIntegerField(
        'Order Id',
        default = 0,
    )

    class Meta:
        ordering = [ 'order_id' ]
        indexes = [
            models.Index( fields=['entity', 'collection' ] ),
        ]
