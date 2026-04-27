"""
HomeBox simulator entity and state definitions.

The simulator's "HomeBox Inventory Item" entity represents a single inventory
item as exposed by the real HomeBox REST API. Item metadata is stored in
HomeBoxInventoryItemFields (persisted via DbSimEntity); the only mutable
runtime state is the ``archived`` flag.

The to_api_dict helper builds the JSON shape the integration's HbItem parser
(src/hi/services/homebox/hb_models.py) consumes.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.utils import str_to_bool

from hi.simulator.base_models import SimEntityFields, SimState, SimEntityDefinition
from hi.simulator.enums import SimEntityType, SimStateType


@dataclass( frozen = True )
class HomeBoxInventoryItemFields( SimEntityFields ):
    """ User-editable metadata for a simulated HomeBox inventory item. """

    description    : str  = ''
    serial_number  : str  = ''
    model_number   : str  = ''
    manufacturer   : str  = ''
    notes          : str  = ''
    quantity       : int  = 1


@dataclass
class HomeBoxItemArchivedState( SimState ):
    """
    Single mutable state per item: the archived flag (boolean).

    Stored as a string ('on'/'off') consistent with how SimStateType.ON_OFF
    is rendered in the simulator UI; converted to a real boolean in the API
    response.
    """

    sim_entity_fields  : HomeBoxInventoryItemFields
    sim_state_type     : SimStateType                 = SimStateType.ON_OFF
    sim_state_id       : str                          = 'archived'
    value              : str                          = 'off'

    @property
    def name(self):
        return f'{self.sim_entity_fields.name} Is Archived?'

    @property
    def is_archived(self) -> bool:
        return str_to_bool( self.value )


HOMEBOX_SIM_ENTITY_DEFINITION_LIST: List[SimEntityDefinition] = [
    SimEntityDefinition(
        class_label             = 'HomeBox Inventory Item',
        sim_entity_type         = SimEntityType.OTHER,
        sim_entity_fields_class = HomeBoxInventoryItemFields,
        sim_state_class_list    = [
            HomeBoxItemArchivedState,
        ],
    ),
]


def build_item_api_dict( sim_entity_id    : int,
                         fields           : HomeBoxInventoryItemFields,
                         archived_state   : HomeBoxItemArchivedState ) -> Dict[ str, Any ]:
    """
    Build the HomeBox item JSON shape returned by the simulator's API,
    matching the fields the integration's HbItem parser consumes.

    Fields not in the simulator's scope (custom fields, attachments,
    location, labels) are emitted as empty/null. Timestamps are emitted
    as the current time on every call; the integration uses them only
    for change detection.
    """
    now_iso = datetimeproxy.now().isoformat()
    return {
        'id'             : str(sim_entity_id),
        'name'           : fields.name,
        'description'    : fields.description,
        'serialNumber'   : fields.serial_number,
        'modelNumber'    : fields.model_number,
        'manufacturer'   : fields.manufacturer,
        'notes'          : fields.notes,
        'quantity'       : fields.quantity,
        'archived'       : archived_state.is_archived,
        'fields'         : [],
        'attachments'    : [],
        'location'       : None,
        'labels'         : [],
        'createdAt'      : now_iso,
        'updatedAt'      : now_iso,
    }
