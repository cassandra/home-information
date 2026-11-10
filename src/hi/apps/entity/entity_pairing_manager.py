from collections import defaultdict
from typing import Dict, List, Sequence, Set

from django.db import transaction

from hi.apps.common.singleton import Singleton
from hi.apps.location.models import LocationView

from . import enums
from . import models
from .entity_state_labels import entity_state_short_labels
from .transient_models import (
    EntityPairing,
    PairingStateColumn,
    PairingStateGrid,
    PairingStateRow,
    PairingStateRowGroup,
)


class EntityPairingError(Exception):
    pass


class EntityPairingManager(Singleton):

    CREATE_BY_DEFAULT_MAP = {
        # Defines which EntityStateType should have a delegate entity by
        # default and the type of entity to create.  Delegations are mainly for
        # visual/view use, so usually only get created when an entity is
        # added to a location view for the first time.

        enums.EntityStateType.MOVEMENT: enums.EntityType.AREA,
        enums.EntityStateType.OBJECT_PRESENCE: enums.EntityType.AREA,
        enums.EntityStateType.PRESENCE: enums.EntityType.AREA,
        enums.EntityStateType.SOUND_LEVEL: enums.EntityType.AREA,
    }
    
    def __init_singleton__(self):
        return

    def get_entity_pairing_list( self, entity : models.Entity ) -> List[ EntityPairing ]:
        entity_pairing_list = list()

        # Entity as delegate: one pair per principal whose states it receives.
        principal_to_delegated_states = defaultdict( list )
        delegation_queryset = entity.entity_state_delegations.select_related(
            'entity_state',
            'entity_state__entity',
        ).all()
        for entity_state_delegation in delegation_queryset:
            entity_state = entity_state_delegation.entity_state
            principal_to_delegated_states[entity_state.entity].append( entity_state )
            continue

        for principal_entity in sorted( principal_to_delegated_states, key = lambda x : x.name ):
            entity_pairing = EntityPairing(
                entity = entity,
                paired_entity = principal_entity,
                pairing_type = enums.EntityPairingType.PRINCIPAL,
                principal_states = list( principal_entity.states.order_by( 'id' )),
                delegated_states = sorted( principal_to_delegated_states[principal_entity],
                                           key = lambda x : x.id ),
            )
            entity_pairing_list.append( entity_pairing )
            continue

        # Entity as principal: one pair per delegate of any of its states.
        principal_states = list( entity.states.order_by( 'id' ))
        delegate_to_delegated_states = defaultdict( list )
        delegation_queryset = models.EntityStateDelegation.objects.filter(
            entity_state__entity = entity,
        ).select_related( 'entity_state', 'delegate_entity' )
        for entity_state_delegation in delegation_queryset:
            delegate_to_delegated_states[entity_state_delegation.delegate_entity].append(
                entity_state_delegation.entity_state
            )
            continue

        for delegate_entity in sorted( delegate_to_delegated_states, key = lambda x : x.name ):
            entity_pairing = EntityPairing(
                entity = entity,
                paired_entity = delegate_entity,
                pairing_type = enums.EntityPairingType.DELEGATE,
                principal_states = principal_states,
                delegated_states = sorted( delegate_to_delegated_states[delegate_entity],
                                           key = lambda x : x.id ),
            )
            entity_pairing_list.append( entity_pairing )
            continue

        return entity_pairing_list
    
    def get_candidate_entities( self, entity : models.Entity ) -> List[ EntityPairing ]:
        """ We only allow pairing entities with states to those without states.  """
        entity_has_states = bool( entity.states.exists() )

        candidate_entity_list = list()
        for candidate_entity in models.Entity.objects.all():
            candidate_entity_has_states = bool( candidate_entity.states.exists() )

            if (( entity_has_states and not candidate_entity_has_states )
                or ( not entity_has_states and candidate_entity_has_states )):
                candidate_entity_list.append( candidate_entity )
                
            continue
        return candidate_entity_list
    
    def get_delegate_entities( self, entity : models.Entity ) -> List[ models.Entity ]:
        delegate_entity_set = set()
        for entity_state in entity.states.all():
            for entity_state_delegation in entity_state.entity_state_delegations.all():
                delegate_entity_set.add( entity_state_delegation.delegate_entity )
                continue
            continue
        delegate_entity_list = list( delegate_entity_set )
        delegate_entity_list.sort( key = lambda entity : entity.name )
        return delegate_entity_list
        
    def get_principal_entities( self, entity : models.Entity ) -> List[ models.Entity ]:
        principal_entity_set = set()
        delegation_queryset = entity.entity_state_delegations.select_related(
            'entity_state',
            'entity_state__entity'
        ).all()
        for entity_state_delegation in delegation_queryset:
            principal_entity_set.add( entity_state_delegation.entity_state.entity )
            continue
        principal_entity_list = list( principal_entity_set )
        principal_entity_list.sort( key = lambda entity : entity.name )
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
                    can_user_delete = True,
                    integration_id = None,
                    integration_name = None,
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

    def adjust_entity_pairings( self, entity : models.Entity, desired_paired_entity_ids : Set[ int ] ):

        previous_entity_pairings = self.get_entity_pairing_list( entity = entity )
        previous_paired_entity_ids = { x.paired_entity.id for x in previous_entity_pairings }

        to_add_entity_ids = desired_paired_entity_ids - previous_paired_entity_ids
        to_delete_entity_ids = previous_paired_entity_ids - desired_paired_entity_ids
        
        entity_has_states = bool( entity.states.exists() )
        to_add_paired_entities = list( models.Entity.objects.filter( id__in = list(to_add_entity_ids) ) )

        for candidate_entity in to_add_paired_entities:
            candidate_entity_has_states = bool( candidate_entity.states.exists() )

            if entity_has_states and candidate_entity_has_states:
                raise EntityPairingError(
                    f'Cannot pair entities both with states: {entity} and {candidate_entity}' )
            if not entity_has_states and not candidate_entity_has_states:
                raise EntityPairingError(
                    f'Cannot pair entities both without states: {entity} and {candidate_entity}' )
            continue

        with transaction.atomic():
            for to_add_entity in to_add_paired_entities:
                if entity_has_states:
                    principle_entity = entity
                    delegate_entity = to_add_entity
                else:
                    principle_entity = to_add_entity
                    delegate_entity = entity
                    
                for entity_state in principle_entity.states.all():
                    models.EntityStateDelegation.objects.create(
                        entity_state = entity_state,
                        delegate_entity = delegate_entity,
                    )
                    continue
                continue

            for to_delete_entity_id in to_delete_entity_ids:
                to_delete_entity = models.Entity.objects.get(id=to_delete_entity_id)
                if entity_has_states:
                    principle_entity = entity
                    delegate_entity = to_delete_entity
                else:
                    principle_entity = to_delete_entity
                    delegate_entity = entity

                delegation_queryset = delegate_entity.entity_state_delegations.select_related(
                    'entity_state',
                    'entity_state__entity' ).all()
                for delegation in delegation_queryset:
                    if delegation.entity_state.entity == principle_entity:
                        delegation.delete()
                    continue
        return

    def get_pairing_state_grid( self,
                                principal_entity  : models.Entity,
                                delegate_entities : Sequence[ models.Entity ] ) -> PairingStateGrid:
        """Grid of the principal's states for the given delegates. A
        delegate already paired starts with the states it receives now;
        a new one starts with all states, as an entity-level pairing
        would give it."""
        principal_states = list( principal_entity.states.order_by( 'id' ))
        short_labels = entity_state_short_labels( principal_states )
        all_state_ids = { x.id for x in principal_states }

        delegate_to_state_ids = defaultdict( set )
        delegation_queryset = models.EntityStateDelegation.objects.filter(
            entity_state__entity = principal_entity,
        )
        for delegation in delegation_queryset:
            delegate_to_state_ids[delegation.delegate_entity_id].add( delegation.entity_state_id )
            continue

        row_group_map = dict()
        for delegate_entity in sorted( delegate_entities, key = lambda x : x.name ):
            entity_group_type = enums.EntityGroupType.from_entity_type( delegate_entity.entity_type )
            if entity_group_type not in row_group_map:
                row_group_map[entity_group_type] = PairingStateRowGroup( entity_group_type = entity_group_type )
            row_group_map[entity_group_type].row_list.append( PairingStateRow(
                entity = delegate_entity,
                delegated_state_ids = delegate_to_state_ids.get( delegate_entity.id, all_state_ids ),
            ))
            continue

        return PairingStateGrid(
            principal_entity = principal_entity,
            column_list = [ PairingStateColumn( entity_state = x, label = short_labels[x.id] )
                            for x in principal_states ],
            row_group_list = sorted( row_group_map.values(), key = lambda x : x.entity_group_type.label ),
        )

    def set_delegated_states( self,
                              principal_entity                 : models.Entity,
                              delegate_entity_id_to_state_ids  : Dict[ int, Set[ int ] ] ):
        """Make the principal's delegations exactly the given ones: each
        delegate receives just the listed states of the principal. A
        delegate absent from the mapping, or mapped to no states, is
        unpaired from this principal. Delegations from other principals
        are not touched."""

        principal_state_ids = set( principal_entity.states.values_list( 'id', flat = True ))
        if not principal_state_ids:
            raise EntityPairingError( f'Cannot delegate states of an entity without states: {principal_entity}' )

        delegate_entity_map = models.Entity.objects.in_bulk( list( delegate_entity_id_to_state_ids.keys() ))
        desired_pairs = set()
        for delegate_entity_id, state_ids in delegate_entity_id_to_state_ids.items():
            delegate_entity = delegate_entity_map.get( delegate_entity_id )
            if not delegate_entity:
                raise EntityPairingError( f'Unknown delegate entity id: {delegate_entity_id}' )
            if delegate_entity.states.exists():
                raise EntityPairingError(
                    f'Cannot pair entities both with states: {principal_entity} and {delegate_entity}' )
            foreign_state_ids = set( state_ids ) - principal_state_ids
            if foreign_state_ids:
                raise EntityPairingError(
                    f'States {sorted(foreign_state_ids)} do not belong to {principal_entity}' )
            desired_pairs.update( ( state_id, delegate_entity_id ) for state_id in state_ids )
            continue

        # Per-object create/delete (not bulk) so model signals fire.
        with transaction.atomic():
            delegation_queryset = models.EntityStateDelegation.objects.filter(
                entity_state__entity = principal_entity,
            )
            existing_pairs = set()
            for delegation in delegation_queryset:
                pair = ( delegation.entity_state_id, delegation.delegate_entity_id )
                if pair in desired_pairs:
                    existing_pairs.add( pair )
                else:
                    delegation.delete()
                continue

            for state_id, delegate_entity_id in desired_pairs - existing_pairs:
                models.EntityStateDelegation.objects.create(
                    entity_state_id = state_id,
                    delegate_entity_id = delegate_entity_id,
                )
                continue
        return
