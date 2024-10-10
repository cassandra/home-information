from .enums import ItemType


class ItemTypeModelMixin:

    @property
    def item_type(self) -> ItemType:
        raise NotImplementedError( 'This method must be implemented.' )
    
    @property
    def html_id(self):
        return self.item_type.html_id( self.id )

