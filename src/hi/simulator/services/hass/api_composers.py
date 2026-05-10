"""
HA API entity composition for the simulator.

The simulator's data model is HI-centric: each runtime-mutable
value HI sees as its own EntityState gets its own SimState (own
min/max range, own slider in the simulator UI). Real HA, however,
emits some devices (color smart bulbs, climate entities) as ONE
HA entity with multiple attributes — not multiple entities. This
module reconciles the two: a per-device-type composer collapses an
entity's SimStates into the HA-shape dict(s) emitted by
``/api/states``.

The default composer keeps the existing one-state-per-HA-entity
behavior so devices already aligned with HA's shape (motion
detectors, switches, sensors) are unaffected. Devices whose HA
shape is "one entity with attributes from N states" register a
custom composer keyed off their ``SimEntityFields`` class.

The dispatch entrypoint is
``HassApiComposer.compose(sim_entity)``; ``AllStatesView`` calls
it per SimEntity and concatenates the results.
"""
from typing import Dict, List

from hi.simulator.base_models import SimState

from .sim_models import (
    HassColorSmartBulbBrightnessState,
    HassColorSmartBulbColorModeState,
    HassColorSmartBulbFields,
    HassMultiFeatureFanFields,
    HassMultiFeatureFanPercentageState,
    HassThermostatFields,
    HassThermostatHvacModeState,
)


class HassApiComposer:
    """Namespace for the HA API entity composers and their
    dispatch. Composers are classmethods so they can reference
    each other and the registry stays close to the implementations.
    """

    @classmethod
    def compose( cls, sim_entity ) -> List[ Dict ]:
        """Public dispatch. Look up the composer registered for
        the sim_entity's fields class; fall back to the default
        (one-state-per-HA-entity) when no specific composer is
        registered. Returns the list of HA-shape api dicts the
        ``/api/states`` endpoint should emit for this entity."""
        fields_class = type( sim_entity.sim_entity_fields )
        composer_fn = cls._REGISTRY.get( fields_class, cls._default )
        return composer_fn( sim_entity.sim_state_list )

    @staticmethod
    def _default( sim_states : List[ SimState ] ) -> List[ Dict ]:
        """Default emission: each SimState becomes its own HA
        entity. Used by the motion detector, switches, sensors —
        anything where the existing one-state-per-entity model
        already matches real HA's shape."""
        return [ s.to_api_dict() for s in sim_states ]

    @staticmethod
    def _color_smart_bulb( sim_states : List[ SimState ] ) -> List[ Dict ]:
        """Compose a color smart bulb's brightness/hue/saturation/
        color-temperature SimStates into ONE HA ``light.x`` entity
        matching real HA's shape. Brightness is the primary state
        (drives the entity's ``state`` field); others contribute
        attributes only. Hue+saturation are combined into the
        standard ``hs_color: [h, s]`` two-element list."""
        primary_dict = None
        merged_attrs : Dict = {}
        color_mode_value = None
        for state in sim_states:
            api_dict = state.to_api_dict()
            if isinstance( state, HassColorSmartBulbBrightnessState ):
                # Primary — clone its api_dict shape (entity_id,
                # state, context, last_changed, etc.), then merge
                # attributes from the other states into its
                # attributes dict.
                primary_dict = dict( api_dict )
            elif isinstance( state, HassColorSmartBulbColorModeState ):
                color_mode_value = state.value
            merged_attrs.update( api_dict.get( 'attributes', {} ) )
            continue

        # Combine the partial hs_hue/hs_saturation contributions
        # into the standard hs_color two-element list.
        hue = merged_attrs.pop( '_partial_hs_hue', None )
        sat = merged_attrs.pop( '_partial_hs_saturation', None )
        if hue is not None and sat is not None:
            merged_attrs[ 'hs_color' ] = [ hue, sat ]

        # ``color_mode`` reflects the dedicated SimState — the
        # service dispatcher writes it when HI sends hs_color or
        # color_temp_kelvin, and the operator can override it
        # directly via the simulator UI for edge-case testing.
        if color_mode_value is not None:
            merged_attrs[ 'color_mode' ] = color_mode_value

        if primary_dict is None:
            # No brightness state in the entity — should not
            # happen in practice with the registered SimEntity
            # shape, but fall back to default behavior so we
            # don't drop the device entirely.
            return HassApiComposer._default( sim_states )

        primary_dict[ 'attributes' ] = merged_attrs
        return [ primary_dict ]

    @staticmethod
    def _multi_feature_fan( sim_states : List[ SimState ] ) -> List[ Dict ]:
        """Compose a multi-feature fan's percentage / oscillating /
        direction / preset SimStates into ONE HA ``fan.x`` entity.
        Percentage is the primary state (drives the entity's
        ``state`` field on/off); the others contribute attributes
        only."""
        primary_dict = None
        merged_attrs : Dict = {}
        for state in sim_states:
            api_dict = state.to_api_dict()
            if isinstance( state, HassMultiFeatureFanPercentageState ):
                primary_dict = dict( api_dict )
            merged_attrs.update( api_dict.get( 'attributes', {} ) )
            continue

        if primary_dict is None:
            return HassApiComposer._default( sim_states )

        primary_dict[ 'attributes' ] = merged_attrs
        return [ primary_dict ]

    @staticmethod
    def _thermostat( sim_states : List[ SimState ] ) -> List[ Dict ]:
        """Compose a thermostat's substate SimStates into ONE HA
        ``climate.x`` entity. The HVAC-mode SimState carries the
        primary state (HA climate's ``state`` field is the active
        hvac_mode). Setpoint shape varies with the active mode:
        ``heat_cool`` emits ``target_temp_low`` /
        ``target_temp_high``, every other mode emits a single
        ``temperature``. Real HA thermostats behave the same way."""
        primary_dict = None
        merged_attrs : Dict = {}
        active_mode = None
        partials : Dict = {}
        temperature_unit = None
        for state in sim_states:
            api_dict = state.to_api_dict()
            if isinstance( state, HassThermostatHvacModeState ):
                primary_dict = dict( api_dict )
                active_mode = state.value
            merged_attrs.update( api_dict.get( 'attributes', {} ) )
            sim_entity_fields = getattr( state, 'sim_entity_fields', None )
            if isinstance( sim_entity_fields, HassThermostatFields ):
                temperature_unit = sim_entity_fields.temperature_unit
            continue

        # Lift partial setpoint contributions into the active-mode
        # shape; drop the partial markers either way so they don't
        # leak into the emitted attributes.
        for partial_key in (
                '_partial_target_temperature',
                '_partial_target_temp_low',
                '_partial_target_temp_high',
        ):
            if partial_key in merged_attrs:
                partials[ partial_key ] = merged_attrs.pop( partial_key )

        if active_mode == 'heat_cool':
            if '_partial_target_temp_low' in partials:
                merged_attrs[ 'target_temp_low' ] = partials[ '_partial_target_temp_low' ]
            if '_partial_target_temp_high' in partials:
                merged_attrs[ 'target_temp_high' ] = partials[ '_partial_target_temp_high' ]
        else:
            if '_partial_target_temperature' in partials:
                merged_attrs[ 'temperature' ] = partials[ '_partial_target_temperature' ]

        if temperature_unit is not None:
            merged_attrs[ 'temperature_unit' ] = temperature_unit

        if primary_dict is None:
            return HassApiComposer._default( sim_states )

        primary_dict[ 'attributes' ] = merged_attrs
        return [ primary_dict ]


# Registry built after the class is defined so the classmethod
# objects exist as references. Keyed off SimEntityFields class so
# the dispatch is per-device-type.
HassApiComposer._REGISTRY = {
    HassColorSmartBulbFields: HassApiComposer._color_smart_bulb,
    HassMultiFeatureFanFields: HassApiComposer._multi_feature_fan,
    HassThermostatFields: HassApiComposer._thermostat,
}
