from django.http import HttpRequest

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityPath
from hi.integrations.core.enums import IntegrationType
from hi.apps.location.models import Location


class EntityEditHelpers:

    @classmethod
    def create_entity( cls,
                       request      : HttpRequest,
                       entity_type  : EntityType,
                       name         : str          ) -> Entity:
        return Entity.objects.create(
            name = name,
            entity_type_str = str(entity_type),
            integration_type_str = str(IntegrationType.NONE),
            integration_key = None,
        )

    @classmethod
    def set_entity_path( cls,
                         entity_id     : int,
                         location      : Location,
                         svg_path_str  : str        ) -> EntityPath:

        try:
            entity_path = EntityPath.objects.get(
                location = location,
                entity_id = entity_id,
            )
            entity_path.svg_path = svg_path_str
            entity_path.save()
            return entity_path
        
        except EntityPath.DoesNotExist:
            pass

        entity = Entity.objects.get( id = entity_id )
        return EntityPath.objects.create(
            entity = entity,
            location = location,
            svg_path = svg_path_str,
        )
            
