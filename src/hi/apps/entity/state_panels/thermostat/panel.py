from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatePanel


_REQUIRED_ROLES = {
    EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
}

_OPTIONAL_ROLES = {
    EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
    EntityStateRole.HVAC_ACTION,
}


modal_panel = EntityStatePanel(
    name             = 'thermostat_modal',
    entity_type      = EntityType.THERMOSTAT,
    display_contexts = { DisplayContext.MODAL },
    priority         = 100,
    template_name    = 'entity/state_panels/thermostat/modal.html',
    required_roles   = _REQUIRED_ROLES,
    optional_roles   = _OPTIONAL_ROLES,
)

list_panel = EntityStatePanel(
    name             = 'thermostat_list',
    entity_type      = EntityType.THERMOSTAT,
    display_contexts = { DisplayContext.LIST },
    priority         = 100,
    template_name    = 'entity/state_panels/thermostat/list.html',
    required_roles   = _REQUIRED_ROLES,
    optional_roles   = _OPTIONAL_ROLES,
)

grid_panel = EntityStatePanel(
    name             = 'thermostat_grid',
    entity_type      = EntityType.THERMOSTAT,
    display_contexts = { DisplayContext.GRID },
    priority         = 100,
    template_name    = 'entity/state_panels/thermostat/grid.html',
    required_roles   = _REQUIRED_ROLES,
    optional_roles   = _OPTIONAL_ROLES,
)
