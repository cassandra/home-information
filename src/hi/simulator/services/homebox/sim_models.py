"""
HomeBox simulator entity and state definitions.

The simulator's "HomeBox Inventory Item" entity represents a single inventory
item as exposed by the real HomeBox REST API. Item metadata is stored in
HomeBoxInventoryItemFields (persisted via DbSimEntity); the only mutable
runtime state is the ``archived`` flag.

The to_api_dict helper builds the JSON shape the integration's HbItem parser
(src/hi/services/homebox/hb_models.py) consumes.
"""

from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List

from hi.apps.common.utils import str_to_bool

from hi.simulator.base_models import SimEntityFields, SimState, SimEntityDefinition
from hi.simulator.enums import SimEntityType, SimStateType

from .attachment_catalog import (
    attachment_choices,
    build_attachment_metadata,
    parse_attachment_keys,
)


@dataclass( frozen = True )
class HomeBoxInventoryItemFields( SimEntityFields ):
    """ User-editable metadata for a simulated HomeBox inventory item.

    ``item_id`` is the identity the simulator's API emits as the
    item's ``id``. Stable across profiles when the operator sets a
    matching value in two profiles (e.g. baseline + baseline-changed
    sharing 'cordless-drill'); when left empty the simulator falls
    back to the row's auto-assigned ``DbSimEntity`` PK, which keeps
    historical UI-created items working but means the same logical
    item in two different profiles ends up with different ids.
    """

    item_id          : str  = ''
    description      : str  = ''
    serial_number    : str  = ''
    model_number     : str  = ''
    manufacturer     : str  = ''
    notes            : str  = ''
    quantity         : int  = 1
    # Comma-separated wire keys of ``AttachmentTemplate`` members
    # (``hi.simulator.services.homebox.attachment_catalog``);
    # unknown keys are dropped silently. The simulator's API
    # download endpoint renders each referenced attachment's
    # bytes on demand, so this is the only place attachments
    # are configured per-item. The ``csv_choices`` metadata hook
    # tells ``SimEntityFieldsForm`` to render this as a
    # multi-checkbox picker over the catalog instead of a free-
    # text input.
    attachment_keys  : str  = dc_field(
        default = '',
        metadata = {
            'csv_choices': attachment_choices,
            'help_text': (
                'Pre-canned simulator attachments to attach to '
                'this item. Each selection is rendered on demand '
                'when the integration fetches it.'
            ),
        },
    )


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
                         archived_state   : HomeBoxItemArchivedState,
                         created_at,
                         updated_at ) -> Dict[ str, Any ]:
    """
    Build the HomeBox item JSON shape returned by the simulator's API,
    matching the fields the integration's HbItem parser consumes.

    Fields not in the simulator's scope (custom fields, location,
    labels) are emitted as empty/null. Attachments are populated
    from the per-item ``attachment_keys`` CSV via the catalog in
    ``attachment_catalog``; the actual bytes are rendered on demand
    by the download endpoint when the integration fetches each
    attachment. Timestamps come from the persisted ``DbSimEntity``
    so they're stable across reads — change only when the operator
    actually edits the row, matching real HomeBox behavior.
    """
    # Prefer the operator-supplied stable id; fall back to the
    # auto-assigned PK for items that don't set one (legacy and
    # UI-created profiles).
    item_id = fields.item_id or str(sim_entity_id)
    attachments = [
        build_attachment_metadata( template )
        for template in parse_attachment_keys( fields.attachment_keys )
    ]
    return {
        'id'             : item_id,
        'name'           : fields.name,
        'description'    : fields.description,
        'serialNumber'   : fields.serial_number,
        'modelNumber'    : fields.model_number,
        'manufacturer'   : fields.manufacturer,
        'notes'          : fields.notes,
        'quantity'       : fields.quantity,
        'archived'       : archived_state.is_archived,
        'fields'         : [],
        'attachments'    : attachments,
        'location'       : None,
        'labels'         : [],
        'createdAt'      : created_at.isoformat(),
        'updatedAt'      : updated_at.isoformat(),
    }
