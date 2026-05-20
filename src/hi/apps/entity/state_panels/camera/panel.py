from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatePanel


_OPTIONAL_ROLES = {
    EntityStateRole.MOVEMENT,
    EntityStateRole.OBJECT_PRESENCE,
}

_ROLE_DATA_TEMPLATE_ALIASES = {
    'motion_data': EntityStateRole.MOVEMENT,
    'object_data': EntityStateRole.OBJECT_PRESENCE,
}


modal_panel = EntityStatePanel(
    name                       = 'camera_modal',
    entity_type                = EntityType.CAMERA,
    display_contexts           = { DisplayContext.MODAL },
    priority                   = 100,
    template_name              = 'entity/state_panels/camera/modal.html',
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)

row_panel = EntityStatePanel(
    name                       = 'camera_row',
    entity_type                = EntityType.CAMERA,
    display_contexts           = { DisplayContext.ROW },
    priority                   = 100,
    template_name              = 'entity/state_panels/camera/row.html',
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)

tile_panel = EntityStatePanel(
    name                       = 'camera_tile',
    entity_type                = EntityType.CAMERA,
    display_contexts           = { DisplayContext.TILE },
    priority                   = 100,
    template_name              = 'entity/state_panels/camera/tile.html',
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)
