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
    HassColorSmartBulbFields,
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
        for state in sim_states:
            api_dict = state.to_api_dict()
            if isinstance( state, HassColorSmartBulbBrightnessState ):
                # Primary — clone its api_dict shape (entity_id,
                # state, context, last_changed, etc.), then merge
                # attributes from the other states into its
                # attributes dict.
                primary_dict = dict( api_dict )
            merged_attrs.update( api_dict.get( 'attributes', {} ) )
            continue

        # Combine the partial hs_hue/hs_saturation contributions
        # into the standard hs_color two-element list.
        hue = merged_attrs.pop( '_partial_hs_hue', None )
        sat = merged_attrs.pop( '_partial_hs_saturation', None )
        if hue is not None and sat is not None:
            merged_attrs[ 'hs_color' ] = [ hue, sat ]

        # ``color_mode`` is set by the composer (not by individual
        # states) so the bulb's active mode is consistent
        # regardless of which states the operator has touched.
        # ``hs`` is HA's most common active mode for color bulbs.
        if 'brightness' in merged_attrs:
            merged_attrs[ 'color_mode' ] = 'hs'

        if primary_dict is None:
            # No brightness state in the entity — should not
            # happen in practice with the registered SimEntity
            # shape, but fall back to default behavior so we
            # don't drop the device entirely.
            return HassApiComposer._default( sim_states )

        primary_dict[ 'attributes' ] = merged_attrs
        return [ primary_dict ]


# Registry built after the class is defined so the classmethod
# objects exist as references. Keyed off SimEntityFields class so
# the dispatch is per-device-type.
HassApiComposer._REGISTRY = {
    HassColorSmartBulbFields: HassApiComposer._color_smart_bulb,
}
