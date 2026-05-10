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

from .sim_models import (
    HassColorSmartBulbFields,
    HassFanFields,
    HassGarageCoverFields,
    HassGenericCoverFields,
    HassLockFields,
    HassMultiFeatureFanFields,
    HassThermostatFields,
    HassWindowBlindCoverFields,
)


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
    def _lock( sim_entity,
               domain   : str,
               service  : str,
               payload  : Dict[ str, Any ],
               ) -> List[ Tuple[ str, str ] ]:
        """Lock domain: ``lock.lock`` and ``lock.unlock`` toggle
        the lock's primary ON_OFF SimState. The state's ``state``
        property maps the value to HA's ``'locked'`` / ``'unlocked'``
        strings on emit."""
        if domain != 'lock':
            return []
        if service == 'lock':
            return [ ( 'lock', 'on' ) ]
        if service == 'unlock':
            return [ ( 'lock', 'off' ) ]
        return []

    @staticmethod
    def _discrete_cover( sim_entity,
                         domain   : str,
                         service  : str,
                         payload  : Dict[ str, Any ],
                         ) -> List[ Tuple[ str, str ] ]:
        """Discrete open/close cover (no position attribute):
        ``open_cover`` / ``close_cover`` toggle the ON_OFF
        SimState. Used by every cover whose HA shape is binary
        — garage doors, generic covers, and any future cover
        device class without ``current_position``."""
        if domain != 'cover':
            return []
        if service == 'open_cover':
            return [ ( 'cover', 'on' ) ]
        if service == 'close_cover':
            return [ ( 'cover', 'off' ) ]
        return []

    @staticmethod
    def _window_blind_cover( sim_entity,
                             domain   : str,
                             service  : str,
                             payload  : Dict[ str, Any ],
                             ) -> List[ Tuple[ str, str ] ]:
        """Window blind cover: ``open_cover`` / ``close_cover``
        snap to 100 / 0; ``set_cover_position`` writes the
        payload's ``position`` value (0-100) to the CONTINUOUS
        SimState."""
        if domain != 'cover':
            return []
        if service == 'open_cover':
            return [ ( 'position', '100' ) ]
        if service == 'close_cover':
            return [ ( 'position', '0' ) ]
        if service == 'set_cover_position':
            position = payload.get( 'position' )
            if position is None:
                return []
            try:
                position_int = int( float( position ) )
            except ( TypeError, ValueError ):
                return []
            return [ ( 'position', str( position_int ) ) ]
        return []

    @staticmethod
    def _fan( sim_entity,
              domain   : str,
              service  : str,
              payload  : Dict[ str, Any ],
              ) -> List[ Tuple[ str, str ] ]:
        """Speed-only fan: ``turn_on`` / ``turn_off`` /
        ``set_percentage`` all act on the percentage SimState.
        ``turn_on`` with no payload defaults to max speed so
        the operator sees an effect; with a ``percentage`` /
        ``percentage_step`` payload, that value is used."""
        if domain != 'fan':
            return []
        if service == 'turn_off':
            return [ ( 'percentage', '0' ) ]
        if service == 'turn_on':
            value_str = HassServiceDispatcher._extract_percentage_value_str( payload )
            if value_str is None:
                value_str = '100'
            return [ ( 'percentage', value_str ) ]
        if service == 'set_percentage':
            value_str = HassServiceDispatcher._extract_percentage_value_str( payload )
            if value_str is None:
                return []
            return [ ( 'percentage', value_str ) ]
        return []

    @staticmethod
    def _multi_feature_fan( sim_entity,
                            domain   : str,
                            service  : str,
                            payload  : Dict[ str, Any ],
                            ) -> List[ Tuple[ str, str ] ]:
        """Multi-feature fan: routes each axis-specific HA service
        to the matching SimState. ``turn_on`` / ``turn_off`` /
        ``set_percentage`` act on the percentage SimState (same
        as the speed-only fan); ``oscillate`` writes the
        oscillating SimState; ``set_direction`` and
        ``set_preset_mode`` write theirs."""
        if domain != 'fan':
            return []
        if service == 'turn_off':
            return [ ( 'percentage', '0' ) ]
        if service == 'turn_on':
            value_str = HassServiceDispatcher._extract_percentage_value_str( payload )
            if value_str is None:
                value_str = '100'
            return [ ( 'percentage', value_str ) ]
        if service == 'set_percentage':
            value_str = HassServiceDispatcher._extract_percentage_value_str( payload )
            if value_str is None:
                return []
            return [ ( 'percentage', value_str ) ]
        if service == 'oscillate':
            osc = payload.get( 'oscillating' )
            if osc is None:
                return []
            return [ ( 'oscillating', 'on' if bool( osc ) else 'off' ) ]
        if service == 'set_direction':
            direction = payload.get( 'direction' )
            if direction not in ( 'forward', 'reverse' ):
                return []
            return [ ( 'direction', direction ) ]
        if service == 'set_preset_mode':
            preset_mode = payload.get( 'preset_mode' )
            if not preset_mode:
                return []
            return [ ( 'preset', str( preset_mode ) ) ]
        return []

    @staticmethod
    def _thermostat( sim_entity,
                     domain   : str,
                     service  : str,
                     payload  : Dict[ str, Any ],
                     ) -> List[ Tuple[ str, str ] ]:
        """Thermostat: routes ``set_temperature`` (with ``temperature``
        / ``target_temp_low`` / ``target_temp_high``) and
        ``set_hvac_mode`` to the matching SimStates. HA's
        ``set_temperature`` service accepts either a single
        ``temperature`` or the low/high pair depending on the
        thermostat's active mode — the dispatcher applies whatever
        the payload carries."""
        if domain != 'climate':
            return []
        updates : List[ Tuple[ str, str ] ] = []
        if service == 'set_temperature':
            for key, sim_state_id in (
                    ( 'temperature', 'target_temperature' ),
                    ( 'target_temp_low', 'target_temp_low' ),
                    ( 'target_temp_high', 'target_temp_high' ),
            ):
                if key in payload:
                    try:
                        numeric = float( payload[ key ] )
                    except ( TypeError, ValueError ):
                        continue
                    updates.append( ( sim_state_id, str( numeric ) ) )
            return updates
        if service == 'set_hvac_mode':
            mode = payload.get( 'hvac_mode' )
            if not mode:
                return []
            return [ ( 'hvac_mode', str( mode ) ) ]
        if service == 'set_fan_mode':
            mode = payload.get( 'fan_mode' )
            if not mode:
                return []
            return [ ( 'fan_mode', str( mode ) ) ]
        return []

    @staticmethod
    def _extract_percentage_value_str( payload : Dict[ str, Any ] ) -> Optional[ str ]:
        """Read fan ``percentage`` from an HA service-call
        payload as a 0-100 integer string. Returns None when the
        payload doesn't carry one."""
        if 'percentage' not in payload:
            return None
        try:
            return str( int( float( payload[ 'percentage' ] ) ) )
        except ( TypeError, ValueError ):
            return None

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
    HassFanFields: HassServiceDispatcher._fan,
    HassGarageCoverFields: HassServiceDispatcher._discrete_cover,
    HassGenericCoverFields: HassServiceDispatcher._discrete_cover,
    HassLockFields: HassServiceDispatcher._lock,
    HassMultiFeatureFanFields: HassServiceDispatcher._multi_feature_fan,
    HassThermostatFields: HassServiceDispatcher._thermostat,
    HassWindowBlindCoverFields: HassServiceDispatcher._window_blind_cover,
}
