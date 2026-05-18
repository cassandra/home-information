from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatePanel


_OPTIONAL_ROLES = {
    EntityStateRole.MOVEMENT,
}

_ROLE_DATA_TEMPLATE_ALIASES = {
    'motion_data': EntityStateRole.MOVEMENT,
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

list_panel = EntityStatePanel(
    name                       = 'camera_list',
    entity_type                = EntityType.CAMERA,
    display_contexts           = { DisplayContext.LIST },
    priority                   = 100,
    template_name              = 'entity/state_panels/camera/list.html',
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)

grid_panel = EntityStatePanel(
    name                       = 'camera_grid',
    entity_type                = EntityType.CAMERA,
    display_contexts           = { DisplayContext.GRID },
    priority                   = 100,
    template_name              = 'entity/state_panels/camera/grid.html',
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)
