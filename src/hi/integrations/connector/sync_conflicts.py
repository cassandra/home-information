"""
Sync-time detection of integration-key conflicts.

Entities own components (Sensors, Controllers) whose integration keys
are unique per integration. A sync conflicts when an upstream item
would take over a component key that a *different* HI entity owns --
e.g., an upstream device regrouped under a new identity while its
states keep their old keys. Applying such an item would violate the
component key constraint or, worse, silently move the component's
history between entities. The sync instead leaves both sides
untouched and reports the conflict so the operator can resolve it
upstream.

The detection is integration-agnostic: each integration supplies the
component keys its upstream items would claim; ownership comes from
the HI side.
"""
from dataclasses import dataclass
from typing import Dict, List, Set

from hi.apps.control.models import Controller
from hi.apps.entity.models import Entity
from hi.apps.sense.models import Sensor
from hi.integrations.transient_models import IntegrationKey


@dataclass
class IntegrationSyncConflict:
    """An upstream item claiming component keys owned by another HI
    entity. ``component_keys`` holds every key of the upstream item
    that ``owner_entity`` owns, sorted for stable reporting."""
    upstream_key    : IntegrationKey
    owner_entity    : Entity
    component_keys  : List[ IntegrationKey ]

    def to_message( self, integration_label : str ) -> str:
        component_names = ', '.join( key.integration_name for key in self.component_keys )
        claim = (
            f'{integration_label} item "{self.upstream_key.integration_name}" includes'
            f' {component_names}, which already belongs to HI item'
            f' "{self.owner_entity.name}"'
        )
        owner_key = self.owner_entity.integration_key
        if owner_key is None:
            # An owner without a valid key is an HI-side data problem;
            # nothing upstream can fix it.
            return (
                f'{claim}, which has no valid integration key. Both were'
                f' left unchanged; check this HI item.'
            )
        return (
            f'{claim} ({owner_key.integration_name}). Both were left'
            f' unchanged; resolve this in {integration_label}.'
        )


class IntegrationSyncConflictDetector:
    """Namespace for conflict detection. Class methods rather than
    module-level functions so call sites carry the
    ``IntegrationSyncConflictDetector.`` prefix."""

    @classmethod
    def load_component_owners( cls, integration_id : str ) -> Dict[ IntegrationKey, List[ Entity ]]:
        """Map each component key of the integration to the entities
        that currently own it. Keys are unique per component model, so
        a key normally has one owner; a Sensor and a Controller with
        the same key on different entities yields two."""
        component_key_to_entity_ids = dict()
        for model_class in ( Sensor, Controller ):
            rows = model_class.objects.filter(
                integration_id = integration_id,
            ).values_list( 'integration_id', 'integration_name', 'entity_state__entity_id' )
            for component_integration_id, component_integration_name, entity_id in rows:
                component_key = IntegrationKey(
                    integration_id = component_integration_id,
                    integration_name = component_integration_name,
                )
                component_key_to_entity_ids.setdefault( component_key, set() ).add( entity_id )
                continue
            continue

        all_entity_ids = set().union( *component_key_to_entity_ids.values() )
        entity_id_to_entity = Entity.objects.in_bulk( all_entity_ids )
        return {
            component_key: [ entity_id_to_entity[ entity_id ] for entity_id in sorted( entity_ids ) ]
            for component_key, entity_ids in component_key_to_entity_ids.items()
        }

    @classmethod
    def find_conflicts(
            cls,
            upstream_key_to_component_keys : Dict[ IntegrationKey, Set[ IntegrationKey ]],
            integration_key_to_entity      : Dict[ IntegrationKey, Entity ],
            component_key_to_owners        : Dict[ IntegrationKey, List[ Entity ]],
    ) -> List[ IntegrationSyncConflict ]:
        """Return one conflict per (upstream item, foreign owner) pair.

        An upstream item's own matched entity (its entry in
        ``integration_key_to_entity``) owning a claimed key is the
        normal update case, not a conflict. Any other owner is.
        """
        conflicts = list()
        for upstream_key, component_keys in upstream_key_to_component_keys.items():
            matched_entity = integration_key_to_entity.get( upstream_key )

            owner_id_to_component_keys = dict()
            owner_id_to_owner = dict()
            for component_key in component_keys:
                for owner in component_key_to_owners.get( component_key, [] ):
                    if matched_entity is not None and owner.id == matched_entity.id:
                        continue
                    owner_id_to_component_keys.setdefault( owner.id, list() ).append( component_key )
                    owner_id_to_owner[ owner.id ] = owner
                    continue
                continue

            for owner_id, owned_component_keys in owner_id_to_component_keys.items():
                conflicts.append( IntegrationSyncConflict(
                    upstream_key = upstream_key,
                    owner_entity = owner_id_to_owner[ owner_id ],
                    component_keys = sorted( owned_component_keys, key = str ),
                ))
                continue
            continue

        conflicts.sort( key = lambda conflict: ( str( conflict.upstream_key ), conflict.owner_entity.id ))
        return conflicts
