from django.http import HttpRequest

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.integrations.core.enums import IntegrationType


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
