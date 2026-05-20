"""Per-EntityType ordering of EntityStateRoles.

Three module-level instances:

- ``ENTITY_STATUS_VIEW_ORDERING`` orders states for the
  EntityStatusView modal listing.
- ``ENTITY_PRIMARY_STATE_ORDERING`` selects the single state whose
  value represents the entity's visual status (the ``status``
  attribute on the entity's rendered element). Used by rendering
  paths that show one entity element — initial location-view
  render, full-entity re-render after a one-click action, etc.
- ``ENTITY_CONTROL_STATE_ORDERING`` selects the state targeted by
  one-click control. Distinct from the visual primary: a light's
  visual primary is brightness, but the one-click target is its
  on/off state. The default is intentionally short (just ``ON_OFF``)
  so unrecognized EntityTypes get a safe toggle-or-skip behavior.

Resolution rule: a per-EntityType override is a *prefix*; roles not
in the override follow in the default order. Roles absent from both
sort to the end."""

from dataclasses import dataclass
from typing import Dict, List

from .enums import EntityStateRole, EntityType


DEFAULT_ENTITY_STATE_ROLE_ORDER : List[ EntityStateRole ] = [
    # Alarm-bearing / safety roles.
    EntityStateRole.SMOKE,
    EntityStateRole.CO,
    EntityStateRole.GAS,
    EntityStateRole.MOISTURE,
    EntityStateRole.OBJECT_PRESENCE,
    EntityStateRole.MOVEMENT,
    EntityStateRole.PRESENCE,
    EntityStateRole.OPEN_CLOSE,

    # Primary control axes.
    EntityStateRole.FAN_SPEED,
    EntityStateRole.LIGHT_BRIGHTNESS,
    EntityStateRole.POWER_LEVEL,
    EntityStateRole.LIGHT_DIMMER,
    EntityStateRole.OPEN_CLOSE_POSITION,

    # Discrete / on-off.
    EntityStateRole.LIGHT_ON_OFF,
    EntityStateRole.ON_OFF,
    EntityStateRole.DISCRETE,
    EntityStateRole.MULTIVALUED,

    # Environmental readings.
    EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
    EntityStateRole.TEMPERATURE,
    EntityStateRole.HUMIDITY,
    EntityStateRole.AIR_PRESSURE,
    EntityStateRole.WIND_SPEED,
    EntityStateRole.LIGHT_LEVEL,
    EntityStateRole.SOUND_LEVEL,
    EntityStateRole.WATER_FLOW,

    # Thermostat setpoints.
    EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_LOW,
    EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
    EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_HIGH,

    # HVAC / fan auxiliary axes.
    EntityStateRole.HVAC_MODE,
    EntityStateRole.HVAC_ACTION,
    EntityStateRole.FAN_MODE,
    EntityStateRole.PRESET_MODE,
    EntityStateRole.SWING_MODE,
    EntityStateRole.FAN_OSCILLATION,
    EntityStateRole.FAN_DIRECTION,
    EntityStateRole.FAN_PRESET_MODE,

    # Color & lighting attributes.
    EntityStateRole.LIGHT_COLOR_TEMPERATURE,
    EntityStateRole.COLOR_TEMPERATURE,
    EntityStateRole.LIGHT_HUE,
    EntityStateRole.HUE,
    EntityStateRole.LIGHT_SATURATION,
    EntityStateRole.SATURATION,
    EntityStateRole.LIGHT_COLOR_MODE,
    EntityStateRole.COLOR_MODE,

    # Utility / maintenance / diagnostic.
    EntityStateRole.ELECTRIC_USAGE,
    EntityStateRole.BANDWIDTH_USAGE,
    EntityStateRole.BATTERY_LEVEL,
    EntityStateRole.HIGH_LOW,
    EntityStateRole.CONNECTIVITY,
    EntityStateRole.DATETIME,

    # Generic fallbacks.
    EntityStateRole.CONTINUOUS,
    EntityStateRole.BLOB,
]


ENTITY_STATUS_VIEW_ENTITY_TYPE_OVERRIDES : Dict[ EntityType, List[ EntityStateRole ] ] = {
    EntityType.THERMOSTAT: [
        EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
        EntityStateRole.HUMIDITY,
        EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_LOW,
        EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
        EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_HIGH,
        EntityStateRole.HVAC_MODE,
        EntityStateRole.HVAC_ACTION,
        EntityStateRole.FAN_MODE,
        EntityStateRole.PRESET_MODE,
        EntityStateRole.SWING_MODE,
    ],
    EntityType.CEILING_FAN: [
        EntityStateRole.FAN_SPEED,
        EntityStateRole.ON_OFF,
        EntityStateRole.FAN_OSCILLATION,
        EntityStateRole.FAN_DIRECTION,
        EntityStateRole.FAN_PRESET_MODE,
    ],
    EntityType.EXHAUST_FAN: [
        EntityStateRole.FAN_SPEED,
        EntityStateRole.ON_OFF,
        EntityStateRole.FAN_OSCILLATION,
        EntityStateRole.FAN_DIRECTION,
        EntityStateRole.FAN_PRESET_MODE,
    ],
    EntityType.LIGHT: [
        EntityStateRole.LIGHT_BRIGHTNESS,
        EntityStateRole.LIGHT_COLOR_TEMPERATURE,
        EntityStateRole.LIGHT_HUE,
        EntityStateRole.LIGHT_SATURATION,
        EntityStateRole.LIGHT_COLOR_MODE,
        EntityStateRole.LIGHT_ON_OFF,
    ],
    EntityType.SMOKE_DETECTOR: [
        EntityStateRole.SMOKE,
        EntityStateRole.BATTERY_LEVEL,
    ],
    EntityType.LEAK_SENSOR: [
        EntityStateRole.MOISTURE,
        EntityStateRole.BATTERY_LEVEL,
    ],
    EntityType.CARBON_MONOXIDE_DETECTOR: [
        EntityStateRole.CO,
        EntityStateRole.BATTERY_LEVEL,
    ],
    EntityType.GAS_DETECTOR: [
        EntityStateRole.GAS,
        EntityStateRole.BATTERY_LEVEL,
    ],
}


@dataclass( frozen = True )
class EntityStateRoleOrdering:

    default_order  : List[ EntityStateRole ]
    overrides      : Dict[ EntityType, List[ EntityStateRole ] ]

    def order_for( self, entity_type : EntityType ) -> List[ EntityStateRole ]:
        override = self.overrides.get( entity_type, [] )
        in_override = set( override )
        tail = [ r for r in self.default_order if r not in in_override ]
        return list( override ) + tail

    def sort_key( self,
                  entity_state_role : EntityStateRole,
                  entity_type       : EntityType ) -> int:
        order = self.order_for( entity_type )
        try:
            return order.index( entity_state_role )
        except ValueError:
            # Defensive: EntityStateRoles not yet placed in the order
            # tables sort to the end.
            return len( order )


ENTITY_STATUS_VIEW_ORDERING = EntityStateRoleOrdering(
    default_order = DEFAULT_ENTITY_STATE_ROLE_ORDER,
    overrides = ENTITY_STATUS_VIEW_ENTITY_TYPE_OVERRIDES,
)


# Primary-state overrides need only declare the winning role
# (position 0); the default order positions the rest. Each entry is
# a sensible starting point; per-EntityType audit can refine later.
ENTITY_PRIMARY_STATE_ENTITY_TYPE_OVERRIDES : Dict[ EntityType, List[ EntityStateRole ] ] = {
    EntityType.THERMOSTAT              : [ EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE ],
    EntityType.CEILING_FAN             : [ EntityStateRole.FAN_SPEED ],
    EntityType.EXHAUST_FAN             : [ EntityStateRole.FAN_SPEED ],
    EntityType.LIGHT                   : [ EntityStateRole.LIGHT_BRIGHTNESS ],
    EntityType.SMOKE_DETECTOR          : [ EntityStateRole.SMOKE ],
    EntityType.LEAK_SENSOR             : [ EntityStateRole.MOISTURE ],
    EntityType.CARBON_MONOXIDE_DETECTOR : [ EntityStateRole.CO ],
    EntityType.GAS_DETECTOR            : [ EntityStateRole.GAS ],
}


ENTITY_PRIMARY_STATE_ORDERING = EntityStateRoleOrdering(
    default_order = DEFAULT_ENTITY_STATE_ROLE_ORDER,
    overrides = ENTITY_PRIMARY_STATE_ENTITY_TYPE_OVERRIDES,
)


# Curated default for one-click control target selection. Each
# entry is a role with universally clear toggle semantics (binary
# pair, or a min/max-bounded continuous slider). EntityTypes without
# a specific override fall through this list in order. Binary roles
# come first so they win when both binary and continuous variants
# exist on the same entity.
#
# Sensor-only roles (MOVEMENT, PRESENCE, SMOKE, MOISTURE, CO, GAS,
# CONNECTIVITY, BATTERY_LEVEL, ...) are intentionally absent: they
# have no controllers in practice and inclusion would only add dead
# matches to _find_controller's eligibility walk.
DEFAULT_CONTROL_STATE_ROLE_ORDER : List[ EntityStateRole ] = [
    EntityStateRole.ON_OFF,
    EntityStateRole.OPEN_CLOSE,
    EntityStateRole.OPEN_CLOSE_POSITION,
    EntityStateRole.POWER_LEVEL,
    EntityStateRole.LIGHT_DIMMER,
]


ENTITY_CONTROL_STATE_ENTITY_TYPE_OVERRIDES : Dict[ EntityType, List[ EntityStateRole ] ] = {
    EntityType.LIGHT              : [ EntityStateRole.LIGHT_ON_OFF,
                                      EntityStateRole.LIGHT_BRIGHTNESS ],
    EntityType.CEILING_FAN        : [ EntityStateRole.FAN_SPEED ],
    EntityType.EXHAUST_FAN        : [ EntityStateRole.FAN_SPEED ],
    EntityType.GARAGE_DOOR_OPENER : [ EntityStateRole.OPEN_CLOSE ],
    # WALL_SWITCH / ON_OFF_SWITCH / ELECTRICAL_OUTLET / DOOR_LOCK
    # rely on the default ON_OFF fallback — no override needed.
}


ENTITY_CONTROL_STATE_ORDERING = EntityStateRoleOrdering(
    default_order = DEFAULT_CONTROL_STATE_ROLE_ORDER,
    overrides = ENTITY_CONTROL_STATE_ENTITY_TYPE_OVERRIDES,
)
