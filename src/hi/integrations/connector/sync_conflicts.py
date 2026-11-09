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

The detection is integration-agnostic and works on *claim keys*: the
upstream identity a component belongs to. By default a component's
claim key is its own integration key; an integration whose components
derive from one upstream record under several keys (e.g., HA substate
keys ``<entity_id>~<suffix>``) maps them all to that record's key.
Comparing at that level keeps detection independent of which derived
components the upstream item would produce this time -- an upstream
record reported with fewer attributes still claims its components.
Each integration supplies the claim keys of its upstream items;
ownership comes from the HI side.
"""
from dataclasses import dataclass
from typing import Callable, Dict, List, Set

from hi.apps.control.models import Controller
from hi.apps.entity.models import Entity
from hi.apps.sense.models import Sensor
from hi.integrations.transient_models import IntegrationKey


@dataclass
class IntegrationSyncConflict:
    """An upstream item claiming keys whose components another HI
    entity owns. ``claim_keys`` holds every claim key of the upstream
    item that ``owner_entity`` owns, sorted for stable reporting."""
    upstream_key  : IntegrationKey
    owner_entity  : Entity
    claim_keys    : List[ IntegrationKey ]

    def to_message( self, integration_label : str ) -> str:
        claim_names = ', '.join( key.integration_name for key in self.claim_keys )
        claim = (
            f'{integration_label} item "{self.upstream_key.integration_name}" includes'
            f' {claim_names}, which already belongs to HI item'
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
    def load_claim_owners(
            cls,
            integration_id             : str,
            component_key_to_claim_key : Callable[ [ IntegrationKey ], IntegrationKey ],
    ) -> Dict[ IntegrationKey, List[ Entity ]]:
        """Map each claim key of the integration's components
        (Sensors and Controllers) to the entities that currently own
        a component under it. A claim key normally has one owner;
        more arise when an inconsistent DB spreads one upstream
        record's components across entities."""
        claim_key_to_entity_ids = dict()
        for model_class in ( Sensor, Controller ):
            rows = model_class.objects.filter(
                integration_id = integration_id,
            ).values_list( 'integration_id', 'integration_name', 'entity_state__entity_id' )
            for component_integration_id, component_integration_name, entity_id in rows:
                claim_key = component_key_to_claim_key( IntegrationKey(
                    integration_id = component_integration_id,
                    integration_name = component_integration_name,
                ))
                claim_key_to_entity_ids.setdefault( claim_key, set() ).add( entity_id )
                continue
            continue

        all_entity_ids = set().union( *claim_key_to_entity_ids.values() )
        entity_id_to_entity = Entity.objects.in_bulk( all_entity_ids )
        return {
            claim_key: [ entity_id_to_entity[ entity_id ] for entity_id in sorted( entity_ids ) ]
            for claim_key, entity_ids in claim_key_to_entity_ids.items()
        }

    @classmethod
    def find_conflicts(
            cls,
            upstream_key_to_claim_keys : Dict[ IntegrationKey, Set[ IntegrationKey ]],
            integration_key_to_entity  : Dict[ IntegrationKey, Entity ],
            claim_key_to_owners        : Dict[ IntegrationKey, List[ Entity ]],
    ) -> List[ IntegrationSyncConflict ]:
        """Return one conflict per (upstream item, foreign owner) pair.

        An upstream item's own matched entity (its entry in
        ``integration_key_to_entity``) owning a claimed key is the
        normal update case, not a conflict. Any other owner is.
        """
        conflicts = list()
        for upstream_key, claim_keys in upstream_key_to_claim_keys.items():
            matched_entity = integration_key_to_entity.get( upstream_key )

            owner_id_to_claim_keys = dict()
            owner_id_to_owner = dict()
            for claim_key in claim_keys:
                for owner in claim_key_to_owners.get( claim_key, [] ):
                    if matched_entity is not None and owner.id == matched_entity.id:
                        continue
                    owner_id_to_claim_keys.setdefault( owner.id, list() ).append( claim_key )
                    owner_id_to_owner[ owner.id ] = owner
                    continue
                continue

            for owner_id, owned_claim_keys in owner_id_to_claim_keys.items():
                conflicts.append( IntegrationSyncConflict(
                    upstream_key = upstream_key,
                    owner_entity = owner_id_to_owner[ owner_id ],
                    claim_keys = sorted( owned_claim_keys, key = str ),
                ))
                continue
            continue

        conflicts.sort( key = lambda conflict: ( str( conflict.upstream_key ), conflict.owner_entity.id ))
        return conflicts
