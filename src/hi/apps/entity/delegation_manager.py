from typing import List

from hi.apps.common.singleton import Singleton
from hi.integrations.core.enums import IntegrationType
from hi.apps.location.models import LocationView

from . import enums
from . import models


class DelegationManager(Singleton):

    CREATE_BY_DEFAULT_MAP = {
        # Defines which EntityStateType should have a delegate entity by
        # default and the type of entity to create.  Delegations are mainly for
        # visual/view use, so usually only get created when an entity is
        # added to a location view for the first time.

        enums.EntityStateType.MOVEMENT: enums.EntityType.AREA,
        enums.EntityStateType.PRESENCE: enums.EntityType.AREA,
        enums.EntityStateType.SOUND_LEVEL: enums.EntityType.AREA,
        enums.EntityStateType.VIDEO_STREAM: enums.EntityType.AREA,
    }
    
    def __init_singleton__(self):
        return

    def get_delegate_entities( self, entity : models.Entity ) -> List[ models.Entity ]:
        delegate_entity_list = list()
        for entity_state in entity.states.all():
            for entity_state_delegation in entity_state.entity_state_delegations.all():
                delegate_entity_list.append( entity_state_delegation.delegate_entity )
                continue
            continue
        return delegate_entity_list
        
    def get_principal_entities( self, entity : models.Entity ) -> List[ models.Entity ]:
        principal_entity_list = list()
        for entity_state_delegation in entity.entity_state_delegations.all():
            principal_entity_list.append( entity_state_delegation.entity_state.entity )
            continue
        return principal_entity_list
        
    def get_delegate_entities_with_defaults( self, entity : models.Entity ) -> List[ models.Entity ]:

        # We only want to create one entity of each entity type.  Multiple
        # states of the entity may need delegates, so we collate the states
        # by entity types.
        #
        entity_type_to_state_list_map = dict()

        # If the entity already has delegates of a given entity type,
        # then we will want to use those instead of creating new ones of
        # the same entity type.
        #
        entity_type_to_delegate_entity_list_map = dict()

        # Used to make sure we do not create a delegation if it already exists.
        entity_state_to_delegate_entity_map = dict()
        
        for entity_state in entity.states.all():

            for entity_state_delegation in entity_state.entity_state_delegations.all():
                entity_state_to_delegate_entity_map[entity_state] = entity_state_delegation.delegate_entity

                delegate_entity = entity_state_delegation.delegate_entity
                entity_type = delegate_entity.entity_type
                if entity_type not in entity_type_to_delegate_entity_list_map:
                    entity_type_to_delegate_entity_list_map[entity_type] = list()
                entity_type_to_delegate_entity_list_map[entity_type].append( delegate_entity )
                continue
            
            if entity_state.entity_state_type not in self.CREATE_BY_DEFAULT_MAP:
                continue
            entity_type = self.CREATE_BY_DEFAULT_MAP[entity_state.entity_state_type]
            if entity_type not in entity_type_to_state_list_map:
                entity_type_to_state_list_map[entity_type] = list()
            entity_type_to_state_list_map[entity_type].append( entity_state )
            continue

        delegate_entity_list = list( entity_state_to_delegate_entity_map.values() )

        for entity_type, entity_state_list in entity_type_to_state_list_map.items():

            entity_states_needing_delegates = set()
            for entity_state in entity_state_list:
                if entity_state in entity_state_to_delegate_entity_map:
                    continue
                entity_states_needing_delegates.add( entity_state )
                continue

            if not entity_states_needing_delegates:
                continue

            if entity_type in entity_type_to_delegate_entity_list_map:
                delegate_entity = entity_type_to_delegate_entity_list_map[entity_type][0]  # Choose first
            else:                
                delegate_entity = models.Entity.objects.create(
                    name = f'{entity.name} - {entity_type.label}',
                    entity_type = entity_type,
                    integration_type_str = str(IntegrationType.NONE),
                    integration_key = None,
                )
                delegate_entity_list.append( delegate_entity )
                
            for entity_state in entity_states_needing_delegates:
                _ = models.EntityStateDelegation.objects.create(
                    entity_state = entity_state,
                    delegate_entity = delegate_entity,
                )
                continue
            continue

        return delegate_entity_list

    def remove_delegate_entities_from_view_if_needed( self,
                                                      entity : models.Entity,
                                                      location_view : LocationView ):
        # We only remove the entity's delegates if the entity is its only principal.
        
        delegate_entities = set( self.get_delegate_entities( entity ))
        for delegate_entity in delegate_entities:
            principal_entities = set( self.get_principal_entities( entity = delegate_entity ))
            if (( len(principal_entities) == 1 )
                and ( next(iter(principal_entities)) == entity )):
                try:
                    entity_view = models.EntityView.objects.get(
                        entity = delegate_entity,
                        location_view = location_view,
                    )
                    entity_view.delete()
                except models.EntityView.DoesNotExist:
                    pass
            continue

        return
