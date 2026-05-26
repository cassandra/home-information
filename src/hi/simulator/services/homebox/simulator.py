from enum import Enum
from typing import List

from hi.simulator.services.base_models import SimEntityDefinition
from hi.simulator.services.service_simulator import ServiceSimulator

from .sim_models import (
    HOMEBOX_SIM_ENTITY_DEFINITION_LIST,
    HomeBoxInventoryItemFields,
    HomeBoxItemArchivedState,
)


class HbApiVersion( Enum ):
    """The HomeBox API surface the simulator serves. v0.25 is the
    legacy ``/v1/items/*`` shape (the only API for HomeBox versions
    up to v0.25). v0.26+ is the ``/v1/entities/*`` shape introduced
    by the entity-merge release. Toggle via the simulator's
    HomeBox-specific settings panel."""

    V0_25 = 'v0.25'
    V0_26 = 'v0.26'

    @classmethod
    def default(cls):
        return cls.V0_25

    @property
    def label(self):
        # Operator-facing label; the value already reads naturally.
        return self.value


class HomeBoxSimulator( ServiceSimulator ):

    def __init_singleton__( self ):
        # Persist the operator-selected API version across SimProfile
        # switches (same pattern as ``_fault_mode``).
        self._api_version = HbApiVersion.default()
        super().__init_singleton__()

    @property
    def id(self):
        return 'hb'

    @property
    def label(self):
        return 'HomeBox'

    @property
    def integration_urls(self):
        return [ ( 'API URL', 'services/homebox/api' ) ]

    @property
    def sim_entity_definition_list(self) -> List[ SimEntityDefinition ]:
        return HOMEBOX_SIM_ENTITY_DEFINITION_LIST

    @property
    def api_version(self) -> HbApiVersion:
        return self._api_version

    def set_api_version( self, api_version: HbApiVersion ):
        self._api_version = api_version
        return

    @property
    def extras_template_name(self):
        return 'homebox/panes/api_version_form.html'

    @property
    def extras_context(self):
        return {
            'api_version': self._api_version,
            'api_version_choices': list( HbApiVersion ),
        }

    def get_sim_entity_pairs(self):
        """
        Iterate (sim_entity_id, fields, archived_state, created_at,
        updated_at) tuples for every configured HomeBox inventory
        item in the active profile. Used by the API views to build
        item responses.

        The two timestamps come from the persisted ``DbSimEntity``
        — stable across reads, only ticking when the operator
        actually edits the row. This matches real HomeBox behavior
        and prevents the converter's payload-equality change
        detection from flagging untouched items as 'updated' on
        every refresh.
        """
        for sim_entity in self._sim_entity_map.values():
            fields = sim_entity.sim_entity_fields
            if not isinstance( fields, HomeBoxInventoryItemFields ):
                continue
            archived_state = sim_entity._sim_state_map.get( 'archived' )
            if not isinstance( archived_state, HomeBoxItemArchivedState ):
                continue
            db_row = sim_entity.db_sim_entity
            yield (
                sim_entity.id,
                fields,
                archived_state,
                db_row.created_datetime,
                db_row.updated_datetime,
            )
