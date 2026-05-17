from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatePanel


_REQUIRED_ROLES = {
    EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
}

_OPTIONAL_ROLES = {
    EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
    EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_LOW,
    EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_HIGH,
    EntityStateRole.HVAC_ACTION,
    EntityStateRole.HVAC_MODE,
    EntityStateRole.FAN_MODE,
    EntityStateRole.PRESET_MODE,
    EntityStateRole.HUMIDITY,
}

# Template variables exposed to the panel templates. Each entry binds a
# template variable name to a declared EntityStateRole; the dispatcher
# resolves these against the per-entity by-role map at render time.
_ROLE_DATA_TEMPLATE_ALIASES = {
    'current_data': EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
    'target_data': EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
    'low_data': EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_LOW,
    'high_data': EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_HIGH,
    'action_data': EntityStateRole.HVAC_ACTION,
    'mode_data': EntityStateRole.HVAC_MODE,
    'fan_data': EntityStateRole.FAN_MODE,
    'preset_data': EntityStateRole.PRESET_MODE,
    'humidity_data': EntityStateRole.HUMIDITY,
}


modal_panel = EntityStatePanel(
    name                       = 'thermostat_modal',
    entity_type                = EntityType.THERMOSTAT,
    display_contexts           = { DisplayContext.MODAL },
    priority                   = 100,
    template_name              = 'entity/state_panels/thermostat/modal.html',
    required_roles             = _REQUIRED_ROLES,
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)

list_panel = EntityStatePanel(
    name                       = 'thermostat_list',
    entity_type                = EntityType.THERMOSTAT,
    display_contexts           = { DisplayContext.LIST },
    priority                   = 100,
    template_name              = 'entity/state_panels/thermostat/list.html',
    required_roles             = _REQUIRED_ROLES,
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)

grid_panel = EntityStatePanel(
    name                       = 'thermostat_grid',
    entity_type                = EntityType.THERMOSTAT,
    display_contexts           = { DisplayContext.GRID },
    priority                   = 100,
    template_name              = 'entity/state_panels/thermostat/grid.html',
    required_roles             = _REQUIRED_ROLES,
    optional_roles             = _OPTIONAL_ROLES,
    role_data_template_aliases = _ROLE_DATA_TEMPLATE_ALIASES,
)
