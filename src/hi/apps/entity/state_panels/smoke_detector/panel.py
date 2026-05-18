from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatePanel


_REQUIRED_ROLES = {
    EntityStateRole.SMOKE,
}

_OPTIONAL_ROLES = {
    EntityStateRole.BATTERY_LEVEL,
}

_ROLE_DATA_TEMPLATE_ALIASES = {
    'smoke_data': EntityStateRole.SMOKE,
    'battery_data': EntityStateRole.BATTERY_LEVEL,
}


modal_panel = EntityStatePanel(
    name                       = 'smoke_detector_modal',
    entity_type                = EntityType.SMOKE_DETECTOR,
    display_contexts           = { DisplayContext.MODAL },
    priority                   = 100,
    template_name              = 'entity/state_panels/smoke_detector/modal.html',
    required_roles             = _REQUIRED_ROLES,
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)

row_panel = EntityStatePanel(
    name                       = 'smoke_detector_row',
    entity_type                = EntityType.SMOKE_DETECTOR,
    display_contexts           = { DisplayContext.ROW },
    priority                   = 100,
    template_name              = 'entity/state_panels/smoke_detector/row.html',
    required_roles             = _REQUIRED_ROLES,
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)

tile_panel = EntityStatePanel(
    name                       = 'smoke_detector_tile',
    entity_type                = EntityType.SMOKE_DETECTOR,
    display_contexts           = { DisplayContext.TILE },
    priority                   = 100,
    template_name              = 'entity/state_panels/smoke_detector/tile.html',
    required_roles             = _REQUIRED_ROLES,
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)
