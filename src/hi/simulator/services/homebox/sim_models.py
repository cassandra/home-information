"""
HomeBox simulator entity and state definitions.

The simulator's "HomeBox Inventory Item" entity represents a single inventory
item as exposed by the real HomeBox REST API. Item metadata is stored in
HomeBoxInventoryItemFields (persisted via DbSimEntity); the only mutable
runtime state is the ``archived`` flag.

The to_api_dict helper builds the JSON shape the integration's HbItem parser
(src/hi/services/homebox/hb_models.py) consumes.
"""

import logging
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List

from hi.apps.common.utils import str_to_bool

from hi.simulator.services.base_models import SimEntityFields, SimState, SimEntityDefinition
from hi.simulator.services.enums import SimEntityType, SimStateType

from .attachment_catalog import (
    attachment_choices,
    build_attachment_metadata,
    parse_attachment_keys,
)


logger = logging.getLogger(__name__)


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

    item_id           : str  = ''
    description       : str  = ''
    serial_number     : str  = ''
    model_number      : str  = ''
    manufacturer      : str  = ''
    asset_id          : str  = ''
    purchase_from     : str  = ''
    purchase_time     : str  = ''
    warranty_details  : str  = ''
    warranty_expires  : str  = ''
    notes             : str  = ''
    quantity          : int  = 1
    custom_fields     : str  = dc_field(
        default = '',
        metadata = {
            'help_text': (
                'Custom user-defined fields. CSV of name=value pairs.'
            ),
        },
    )
    tags              : str  = dc_field(
        default = '',
        metadata = {
            'help_text': 'CSV of HomeBox tag names.',
        },
    )
    location_name     : str  = dc_field(
        default = '',
        metadata = {
            'help_text': (
                'HomeBox location name. When set, the simulator emits a '
                'location dict on the item; when blank, location is null.'
            ),
        },
    )
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


def _parse_custom_fields( csv_value : str ) -> List[ Dict[ str, Any ] ]:
    """Parse the operator's ``custom_fields`` CSV (``name=value``
    pairs) into the HomeBox-style field dict shape. Malformed pairs
    (missing ``=`` or blank name) are dropped with a debug log."""
    if not csv_value:
        return []
    parsed: List[ Dict[ str, Any ] ] = []
    index = 0
    for raw_pair in csv_value.split( ',' ):
        pair = raw_pair.strip()
        if not pair:
            continue
        if '=' not in pair:
            logger.debug( f'Ignoring malformed custom field "{pair}"' )
            continue
        name_part, value_part = pair.split( '=', 1 )
        name = name_part.strip()
        value = value_part.strip()
        if not name:
            logger.debug( f'Ignoring custom field with empty name "{pair}"' )
            continue
        parsed.append({
            'id'           : f'custom-{index + 1}',
            'name'         : name,
            'textValue'    : value,
            'type'         : 'text',
            'numberValue'  : None,
            'booleanValue' : None,
        })
        index += 1
    return parsed


def _parse_tags( csv_value : str ) -> List[ Dict[ str, str ] ]:
    """Parse the operator's ``tags`` CSV into the HomeBox-style tag
    dict shape. Blank entries are skipped."""
    if not csv_value:
        return []
    tags: List[ Dict[ str, str ] ] = []
    index = 0
    for raw_name in csv_value.split( ',' ):
        name = raw_name.strip()
        if not name:
            continue
        tags.append({
            'id'   : f'tag-{index + 1}',
            'name' : name,
        })
        index += 1
    return tags


def _build_location( location_name : str ):
    name = ( location_name or '' ).strip()
    if not name:
        return None
    slug = '-'.join( name.lower().split() )
    return {
        'id'   : f'loc-{slug}',
        'name' : name,
    }


def build_item_api_dict( sim_entity_id    : int,
                         fields           : HomeBoxInventoryItemFields,
                         archived_state   : HomeBoxItemArchivedState,
                         created_at,
                         updated_at ) -> Dict[ str, Any ]:
    """
    Build the HomeBox item JSON shape returned by the simulator's API,
    matching the fields the integration's HbItem parser consumes.

    Location is emitted as a minimal dict (``{id, name}``) when the
    operator sets ``location_name``, else null. The ``id`` is derived
    deterministically from the name so two items sharing a location
    name share a location id. Custom fields, tags, and attachments
    are populated from per-item CSV inputs; the actual attachment
    bytes are rendered on demand by the download endpoint when the
    integration fetches each attachment. Timestamps come from the persisted ``DbSimEntity``
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
        'id'               : item_id,
        'name'             : fields.name,
        'description'      : fields.description,
        'serialNumber'     : fields.serial_number,
        'modelNumber'      : fields.model_number,
        'manufacturer'     : fields.manufacturer,
        'assetId'          : fields.asset_id,
        'purchaseFrom'     : fields.purchase_from,
        'purchaseTime'     : fields.purchase_time,
        'warrantyDetails'  : fields.warranty_details,
        'warrantyExpires'  : fields.warranty_expires,
        'notes'            : fields.notes,
        'quantity'         : fields.quantity,
        'archived'         : archived_state.is_archived,
        'fields'           : _parse_custom_fields( fields.custom_fields ),
        'attachments'      : attachments,
        'location'         : _build_location( fields.location_name ),
        'tags'             : _parse_tags( fields.tags ),
        'createdAt'        : created_at.isoformat(),
        'updatedAt'        : updated_at.isoformat(),
    }


# Sentinel entity type emitted on every v0.26 response. The
# simulator doesn't model the user-definable entity-type system
# from the real HomeBox v0.26+ — every simulated row is an
# inventory item, which maps to the default "Item" type. The id
# stays constant so consumers that key off it see stable values
# across reads.
_DEFAULT_ENTITY_TYPE = {
    'id'         : 'entity-type-item',
    'name'       : 'Item',
    'isLocation' : False,
}


def build_entity_api_dict( sim_entity_id    : int,
                           fields           : HomeBoxInventoryItemFields,
                           archived_state   : HomeBoxItemArchivedState,
                           created_at,
                           updated_at ) -> Dict[ str, Any ]:
    """
    Build the HomeBox v0.26 entity JSON shape returned by the
    simulator's ``/v1/entities/*`` endpoints. Same content as
    ``build_item_api_dict`` with two response-shape differences:

      - The ``location`` field is renamed to ``parent`` (locations
        are entities themselves in v0.26 and can nest under other
        location-type entities; for the simulator the parent is
        always a leaf location, mirroring v0.25 semantics).
      - A new ``entityType`` discriminator is included on every
        entity. The simulator emits a single static "Item" type
        since it does not model the user-definable type system.

    Consumed by ``_HbEntitiesBackend`` (#373 phase 3); the field
    normalization on that backend renames ``parent`` back to
    ``location`` so downstream code stays version-agnostic.
    """
    base = build_item_api_dict(
        sim_entity_id  = sim_entity_id,
        fields         = fields,
        archived_state = archived_state,
        created_at     = created_at,
        updated_at     = updated_at,
    )
    parent = base.pop( 'location' )
    base['parent'] = parent
    base['entityType'] = dict( _DEFAULT_ENTITY_TYPE )
    return base


def build_paginated_envelope( items: list ) -> Dict[ str, Any ]:
    """Wrap a list of entity dicts in the v0.26 paginated response
    shape. The simulator returns everything in one page (sentinel
    ``page=-1``/``pageSize=-1`` matches v0.25's "no pagination"
    convention) — the entities backend always passes an explicit
    ``pageSize`` and loops on ``total`` regardless, so this is
    safe."""
    return {
        'page'       : -1,
        'pageSize'   : -1,
        'total'      : len( items ),
        'items'      : items,
        'totalPrice' : 0,
    }
