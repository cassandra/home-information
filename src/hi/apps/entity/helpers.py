from hi.apps.location.models import Location

from .models import Entity, EntityPosition


class EntityHelpers:

    @classmethod
    def get_entity_position( cls,
                             entity_id  : int,
                             location   : Location ) -> EntityPosition:
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            return None
        
        entity_position = EntityPosition.objects.filter(
            entity = entity,
            location = location,
        ).first()
        if entity_position:
            return entity_position
        return EntityPosition(
            entity = entity,
            location = location,
        )
