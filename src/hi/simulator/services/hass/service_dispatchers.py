"""
HA service-call dispatch for the simulator.

Inverse direction of ``api_composers``: when HA's REST service-call
endpoint receives ``light.turn_on`` (etc.) the simulator must
translate the call into one or more SimState updates on the target
entity. For simple devices (an Insteon switch with one ON_OFF
SimState) this is a 1-to-1 mapping. For composite devices (color
smart bulb with brightness/hue/saturation/color-temp SimStates,
future climate entities with multiple setpoint states) one HA
service call can carry attributes that route to different
SimStates within the same entity.

The dispatcher's job is to read the (domain, service, payload)
shape and emit a list of (sim_state_id, value_str) pairs for the
caller to apply. Per-device-type registry keyed off
``SimEntityFields`` class; the default handler covers the simple
single-state cases (switch on/off, light on/off with optional
brightness payload), so most device types get correct round-trip
behavior without registering a custom handler.

Naming: ``brightness`` here refers to HA's 1-255 attribute (or
``brightness_pct`` 0-100, which the dispatcher converts).
``hs_color`` is HA's standard ``[hue, saturation]`` two-element
list. ``color_temp_kelvin`` is degrees Kelvin.
"""
from typing import Any, Dict, List, Optional, Tuple

from hi.simulator.enums import SimStateType

from .sim_models import HassColorSmartBulbFields


class HassServiceDispatcher:
    """Namespace for the per-device-type service-call handlers and
    their dispatch."""

    @classmethod
    def dispatch( cls,
                  sim_entity,
                  domain   : str,
                  service  : str,
                  payload  : Dict[ str, Any ],
                  ) -> List[ Tuple[ str, str ] ]:
        """Public dispatch entrypoint. Returns a list of
        ``(sim_state_id, value_str)`` pairs the caller should apply
        via ``sim_entity.set_sim_state(...)``. An empty list means
        the service is unsupported for this entity (caller logs
        and falls through). Unknown sim_state_ids in the returned
        list are caller-visible bugs in the handler."""
        fields_class = type( sim_entity.sim_entity_fields )
        handler = cls._REGISTRY.get( fields_class, cls._default )
        return handler( sim_entity, domain, service, payload )

    @staticmethod
    def _default( sim_entity,
                  domain   : str,
                  service  : str,
                  payload  : Dict[ str, Any ],
                  ) -> List[ Tuple[ str, str ] ]:
        """Default dispatch for single-state devices.

        Switch / outlet domains: literal ``on``/``off`` value
        strings on the primary SimState — works for ON_OFF state
        types whose ``state`` property uses ``str_to_bool``.

        Light domain: brightness-aware. ``turn_on`` with a
        ``brightness`` or ``brightness_pct`` payload writes the
        numeric to the primary SimState. ``turn_on`` without a
        brightness payload turns on at the SimState's max value
        for CONTINUOUS states (so dimmers light up fully) or the
        literal ``on`` for ON_OFF states. ``turn_off`` writes 0
        for CONTINUOUS, ``off`` for ON_OFF — without this, the
        old hard-coded ``off`` literal would have polluted a
        CONTINUOUS state's value with a non-numeric string."""
        if not sim_entity.sim_state_list:
            return []
        primary = sim_entity.sim_state_list[ 0 ]

        if ( domain, service ) == ( 'switch', 'turn_on' ):
            return [ ( primary.sim_state_id, 'on' ) ]
        if ( domain, service ) == ( 'switch', 'turn_off' ):
            return [ ( primary.sim_state_id, 'off' ) ]

        if domain == 'light':
            if service == 'turn_on':
                value_str = HassServiceDispatcher._extract_brightness_value_str( payload )
                if value_str is None:
                    if primary.sim_state_type == SimStateType.CONTINUOUS:
                        value_str = str( primary.max_value )
                    else:
                        value_str = 'on'
                return [ ( primary.sim_state_id, value_str ) ]
            if service == 'turn_off':
                if primary.sim_state_type == SimStateType.CONTINUOUS:
                    return [ ( primary.sim_state_id, '0' ) ]
                return [ ( primary.sim_state_id, 'off' ) ]

        return []

    @staticmethod
    def _color_smart_bulb( sim_entity,
                           domain   : str,
                           service  : str,
                           payload  : Dict[ str, Any ],
                           ) -> List[ Tuple[ str, str ] ]:
        """Color smart bulb's ``light.turn_on`` can carry any of
        ``brightness`` / ``brightness_pct`` / ``hs_color`` /
        ``color_temp_kelvin`` / ``rgb_color`` — each routes to a
        different SimState within the bulb. ``turn_off`` sets the
        brightness state to 0 (the bulb's ``state`` field derives
        from brightness). With no payload at all, ``turn_on``
        defaults to full brightness so the bulb actually lights
        up rather than no-opping."""
        if domain != 'light':
            return []
        if service == 'turn_off':
            return [ ( 'brightness', '0' ) ]
        if service != 'turn_on':
            return []

        updates : List[ Tuple[ str, str ] ] = []

        brightness_value = HassServiceDispatcher._extract_brightness_value_str( payload )
        if brightness_value is not None:
            updates.append( ( 'brightness', brightness_value ) )

        hs_color = payload.get( 'hs_color' )
        if isinstance( hs_color, list ) and len( hs_color ) == 2:
            updates.append( ( 'hue', str( hs_color[ 0 ] ) ) )
            updates.append( ( 'saturation', str( hs_color[ 1 ] ) ) )
            # Mirrors HA's behavior: writing hs_color makes hs the
            # active color_mode.
            updates.append( ( 'color_mode', 'hs' ) )

        color_temp = payload.get( 'color_temp_kelvin' )
        if color_temp is not None:
            updates.append( ( 'color_temp', str( int( color_temp ) ) ) )
            updates.append( ( 'color_mode', 'color_temp' ) )

        # ``rgb_color`` is accepted on the wire but not modeled —
        # the bulb's color is driven by hs_color/color_temp in this
        # simulator. HI's color picker (Phase 3) chooses one mode
        # at a time, so leaving rgb out keeps the surface bounded.

        if not updates:
            # Bare turn_on without payload: light up at full
            # brightness so the operator sees an effect.
            updates.append( ( 'brightness', '255' ) )
        return updates

    @staticmethod
    def _extract_brightness_value_str( payload : Dict[ str, Any ] ) -> Optional[ str ]:
        """Read brightness from an HA service-call payload as a
        string suitable for a CONTINUOUS sim state (HA 0-255).
        HA accepts either ``brightness`` (1-255 absolute) or
        ``brightness_pct`` (0-100 percentage); convert pct to
        the absolute scale so the SimState always holds the
        absolute value."""
        if 'brightness' in payload:
            try:
                return str( int( payload[ 'brightness' ] ) )
            except ( TypeError, ValueError ):
                return None
        if 'brightness_pct' in payload:
            try:
                pct = float( payload[ 'brightness_pct' ] )
            except ( TypeError, ValueError ):
                return None
            return str( round( pct * 255 / 100 ) )
        return None


# Registry built after the class is defined so the staticmethod
# objects exist as references. Keyed off SimEntityFields class.
HassServiceDispatcher._REGISTRY = {
    HassColorSmartBulbFields: HassServiceDispatcher._color_smart_bulb,
}
