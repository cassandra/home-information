from typing import Optional

from .hass_models import HassApi, HassServiceCall


class ControlIntent:
    """Canonical operator intents flowing across the HI->HA
    bridge. ``HassConverter.to_ha_on_off_intent`` produces these
    from HI control values; ``HassServiceComposer`` dispatches
    on them to pick the right HA service name."""

    ON = 'on'
    OFF = 'off'
    OPEN = 'open'
    CLOSE = 'close'


class HassServiceComposer:
    """Pure HA-side service-call composition. Methods take
    HA-namespace inputs (already-converted values, payload flags,
    canonical intents) and produce ``HassServiceCall``. They do
    not interpret HI control values directly — when an HI value
    is needed, callers convert via ``HassConverter.to_ha_*``
    boundary methods first."""

    _PAYLOAD_INTENT_SERVICE_KEYS = {
        ControlIntent.ON: 'on_service',
        ControlIntent.OFF: 'off_service',
        ControlIntent.OPEN: 'open_service',
        ControlIntent.CLOSE: 'close_service',
    }

    @classmethod
    def for_payload_intent(
            cls,
            domain           : str,
            hass_substate_id : str,
            intent           : str,
            domain_payload   : dict,
    ) -> Optional[HassServiceCall]:
        """Compose a service call from the matching ``*_service``
        field on the payload. Returns None when the payload does
        not define a service for this intent (caller falls back
        to best-effort)."""
        service_key = cls._PAYLOAD_INTENT_SERVICE_KEYS.get( intent )
        if not service_key:
            raise ValueError( f'Unknown control intent: {intent}' )
        service = domain_payload.get( service_key )
        if not service:
            return None
        return HassServiceCall(
            domain = domain,
            service = service,
            hass_entity_id = hass_substate_id,
        )

    @classmethod
    def for_on_off_best_effort(
            cls,
            domain           : str,
            hass_substate_id : str,
            intent           : str,
    ) -> HassServiceCall:
        if intent == ControlIntent.ON:
            service = HassApi.TURN_ON_SERVICE
        elif intent == ControlIntent.OFF:
            service = HassApi.TURN_OFF_SERVICE
        elif intent == ControlIntent.OPEN:
            if domain == HassApi.COVER_DOMAIN:
                service = HassApi.OPEN_COVER_SERVICE
            elif domain == HassApi.LOCK_DOMAIN:
                service = HassApi.UNLOCK_SERVICE
            else:
                service = HassApi.TURN_ON_SERVICE
        elif intent == ControlIntent.CLOSE:
            if domain == HassApi.COVER_DOMAIN:
                service = HassApi.CLOSE_COVER_SERVICE
            elif domain == HassApi.LOCK_DOMAIN:
                service = HassApi.LOCK_SERVICE
            else:
                service = HassApi.TURN_OFF_SERVICE
        else:
            raise ValueError( f'Unknown control intent: {intent}' )
        return HassServiceCall(
            domain = domain,
            service = service,
            hass_entity_id = hass_substate_id,
        )

    @classmethod
    def for_numeric_best_effort(
            cls,
            domain           : str,
            hass_substate_id : str,
            numeric_value    : float,
    ) -> HassServiceCall:
        if domain == HassApi.LIGHT_DOMAIN:
            brightness_pct = int( numeric_value )
            if not ( 0 <= brightness_pct <= 100 ):
                raise ValueError(
                    f'Invalid brightness value: {brightness_pct} (must be 0-100)'
                )
            if brightness_pct == 0:
                return HassServiceCall(
                    domain = domain,
                    service = HassApi.TURN_OFF_SERVICE,
                    hass_entity_id = hass_substate_id,
                    service_data = None,
                )
            return HassServiceCall(
                domain = domain,
                service = HassApi.TURN_ON_SERVICE,
                hass_entity_id = hass_substate_id,
                service_data = { HassApi.BRIGHTNESS_PCT_PARAM: brightness_pct },
            )
        if domain == HassApi.CLIMATE_DOMAIN:
            return HassServiceCall(
                domain = domain,
                service = HassApi.SET_TEMPERATURE_SERVICE,
                hass_entity_id = hass_substate_id,
                service_data = { HassApi.TARGET_TEMPERATURE_ATTR: numeric_value },
            )
        if domain == HassApi.COVER_DOMAIN:
            position_pct = int( numeric_value )
            if not ( 0 <= position_pct <= 100 ):
                raise ValueError(
                    f'Invalid position value: {position_pct} (must be 0-100)'
                )
            return HassServiceCall(
                domain = domain,
                service = HassApi.SET_COVER_POSITION_SERVICE,
                hass_entity_id = hass_substate_id,
                service_data = { HassApi.POSITION_PARAM: position_pct },
            )
        if domain == HassApi.MEDIA_PLAYER_DOMAIN:
            if not ( 0.0 <= numeric_value <= 1.0 ):
                raise ValueError(
                    f'Invalid volume value: {numeric_value} (must be 0.0-1.0)'
                )
            return HassServiceCall(
                domain = domain,
                service = HassApi.VOLUME_SET_SERVICE,
                hass_entity_id = hass_substate_id,
                service_data = { HassApi.VOLUME_LEVEL_PARAM: numeric_value },
            )
        raise ValueError( f'No numeric control pattern for domain: {domain}' )

    @classmethod
    def for_numeric_parameter(
            cls,
            domain           : str,
            hass_substate_id : str,
            numeric_value    : float,
            domain_payload   : dict,
    ) -> HassServiceCall:
        if domain_payload.get( 'supports_brightness', False ):
            return cls.for_brightness(
                domain = domain,
                hass_substate_id = hass_substate_id,
                brightness = numeric_value,
                domain_payload = domain_payload,
            )
        parameters = domain_payload.get( 'parameters', {} )
        if HassApi.TARGET_TEMPERATURE_ATTR in parameters:
            return cls.for_temperature(
                domain = domain,
                hass_substate_id = hass_substate_id,
                temperature = numeric_value,
                domain_payload = domain_payload,
            )
        if HassApi.VOLUME_LEVEL_PARAM in parameters:
            return cls.for_volume(
                domain = domain,
                hass_substate_id = hass_substate_id,
                volume = numeric_value,
                domain_payload = domain_payload,
            )
        if HassApi.POSITION_PARAM in parameters:
            return cls.for_position(
                domain = domain,
                hass_substate_id = hass_substate_id,
                position = numeric_value,
                domain_payload = domain_payload,
            )
        if HassApi.PERCENTAGE_ATTR in parameters:
            return cls.for_percentage(
                domain = domain,
                hass_substate_id = hass_substate_id,
                percentage = numeric_value,
                domain_payload = domain_payload,
            )
        if domain_payload.get( 'set_service' ):
            service = domain_payload[ 'set_service' ]
            return HassServiceCall(
                domain = domain,
                service = service,
                hass_entity_id = hass_substate_id,
                service_data = { domain.rstrip( 's' ): numeric_value },
            )
        raise ValueError( 'No numeric parameter handling defined' )

    @classmethod
    def for_brightness(
            cls,
            domain           : str,
            hass_substate_id : str,
            brightness       : float,
            domain_payload   : dict,
    ) -> HassServiceCall:
        brightness_pct = int( brightness )
        if not ( 0 <= brightness_pct <= 100 ):
            raise ValueError( f'Invalid brightness value: {brightness}' )
        if brightness_pct == 0:
            service = domain_payload.get( 'off_service' )
            service_data = None
        else:
            service = domain_payload.get( 'on_service' )
            service_data = { HassApi.BRIGHTNESS_PCT_PARAM: brightness_pct }
        if not service:
            raise ValueError( 'No service defined for brightness control' )
        return HassServiceCall(
            domain = domain,
            service = service,
            hass_entity_id = hass_substate_id,
            service_data = service_data,
        )

    @classmethod
    def for_temperature(
            cls,
            domain           : str,
            hass_substate_id : str,
            temperature      : float,
            domain_payload   : dict,
    ) -> HassServiceCall:
        service = domain_payload.get( 'set_service' )
        if not service:
            raise ValueError( 'No temperature service defined' )
        return HassServiceCall(
            domain = domain,
            service = service,
            hass_entity_id = hass_substate_id,
            service_data = { HassApi.TARGET_TEMPERATURE_ATTR: temperature },
        )

    @classmethod
    def for_temperature_range(
            cls,
            domain           : str,
            hass_substate_id : str,
            low              : float,
            high             : float,
    ) -> HassServiceCall:
        """``climate.set_temperature`` with the dual-setpoint
        shape used in ``heat_cool`` mode. HA expects both bounds
        in the same call; the caller is responsible for
        composing the unchanged partner from cached state."""
        if low > high:
            raise ValueError(
                f'Invalid temperature range: low={low} > high={high}'
            )
        return HassServiceCall(
            domain = domain,
            service = HassApi.SET_TEMPERATURE_SERVICE,
            hass_entity_id = hass_substate_id,
            service_data = {
                HassApi.TARGET_TEMP_LOW_ATTR: low,
                HassApi.TARGET_TEMP_HIGH_ATTR: high,
            },
        )

    @classmethod
    def for_hvac_mode(
            cls,
            domain           : str,
            hass_substate_id : str,
            hvac_mode        : str,
    ) -> HassServiceCall:
        if not hvac_mode:
            raise ValueError( 'hvac_mode must be a non-empty string' )
        return HassServiceCall(
            domain = domain,
            service = HassApi.SET_HVAC_MODE_SERVICE,
            hass_entity_id = hass_substate_id,
            service_data = { HassApi.HVAC_MODE_ATTR: hvac_mode },
        )

    @classmethod
    def for_fan_mode(
            cls,
            domain           : str,
            hass_substate_id : str,
            fan_mode         : str,
    ) -> HassServiceCall:
        if not fan_mode:
            raise ValueError( 'fan_mode must be a non-empty string' )
        return HassServiceCall(
            domain = domain,
            service = HassApi.SET_FAN_MODE_SERVICE,
            hass_entity_id = hass_substate_id,
            service_data = { HassApi.FAN_MODE_ATTR: fan_mode },
        )

    @classmethod
    def for_volume(
            cls,
            domain           : str,
            hass_substate_id : str,
            volume           : float,
            domain_payload   : dict,
    ) -> HassServiceCall:
        if not ( 0.0 <= volume <= 1.0 ):
            raise ValueError( f'Invalid volume value: {volume} (must be 0.0-1.0)' )
        service = domain_payload.get( 'set_service', HassApi.VOLUME_SET_SERVICE )
        return HassServiceCall(
            domain = domain,
            service = service,
            hass_entity_id = hass_substate_id,
            service_data = { HassApi.VOLUME_LEVEL_PARAM: volume },
        )

    @classmethod
    def for_position(
            cls,
            domain           : str,
            hass_substate_id : str,
            position         : float,
            domain_payload   : dict,
    ) -> HassServiceCall:
        position_pct = int( position )
        if not ( 0 <= position_pct <= 100 ):
            raise ValueError(
                f'Invalid position value: {position} (must be 0-100)'
            )
        service = domain_payload.get( 'set_service', HassApi.SET_COVER_POSITION_SERVICE )
        return HassServiceCall(
            domain = domain,
            service = service,
            hass_entity_id = hass_substate_id,
            service_data = { HassApi.POSITION_PARAM: position_pct },
        )

    @classmethod
    def for_percentage(
            cls,
            domain           : str,
            hass_substate_id : str,
            percentage       : float,
            domain_payload   : dict,
    ) -> HassServiceCall:
        percentage_int = int( percentage )
        if not ( 0 <= percentage_int <= 100 ):
            raise ValueError(
                f'Invalid percentage value: {percentage} (must be 0-100)'
            )
        service = domain_payload.get( 'set_service', HassApi.SET_PERCENTAGE_SERVICE )
        return HassServiceCall(
            domain = domain,
            service = service,
            hass_entity_id = hass_substate_id,
            service_data = { HassApi.PERCENTAGE_ATTR: percentage_int },
        )

    @classmethod
    def for_oscillating(
            cls,
            domain           : str,
            hass_substate_id : str,
            oscillating      : bool,
    ) -> HassServiceCall:
        return HassServiceCall(
            domain = domain,
            service = HassApi.OSCILLATE_SERVICE,
            hass_entity_id = hass_substate_id,
            service_data = { HassApi.OSCILLATING_ATTR: bool( oscillating ) },
        )

    @classmethod
    def for_motion_detection(
            cls,
            domain           : str,
            hass_substate_id : str,
            enabled          : bool,
    ) -> HassServiceCall:
        """Camera ``motion_detection`` toggle. HA exposes two distinct
        services (``enable_motion_detection`` / ``disable_motion_detection``)
        rather than a single parametric one — same pattern as
        ``lock`` / ``unlock`` and ``open_cover`` / ``close_cover``."""
        service = (
            HassApi.ENABLE_MOTION_DETECTION_SERVICE if enabled
            else HassApi.DISABLE_MOTION_DETECTION_SERVICE
        )
        return HassServiceCall(
            domain = domain,
            service = service,
            hass_entity_id = hass_substate_id,
        )

    @classmethod
    def for_direction(
            cls,
            domain           : str,
            hass_substate_id : str,
            direction        : str,
    ) -> HassServiceCall:
        if direction not in ( 'forward', 'reverse' ):
            raise ValueError(
                f'Invalid fan direction: {direction} (must be forward/reverse)'
            )
        return HassServiceCall(
            domain = domain,
            service = HassApi.SET_DIRECTION_SERVICE,
            hass_entity_id = hass_substate_id,
            service_data = { HassApi.DIRECTION_ATTR: direction },
        )

    @classmethod
    def for_preset_mode(
            cls,
            domain           : str,
            hass_substate_id : str,
            preset_mode      : str,
    ) -> HassServiceCall:
        if not preset_mode:
            raise ValueError( 'preset_mode must be a non-empty string' )
        return HassServiceCall(
            domain = domain,
            service = HassApi.SET_PRESET_MODE_SERVICE,
            hass_entity_id = hass_substate_id,
            service_data = { HassApi.PRESET_MODE_ATTR: preset_mode },
        )

    @classmethod
    def for_color_temp(
            cls,
            domain           : str,
            parent_entity_id : str,
            kelvin           : int,
    ) -> HassServiceCall:
        return HassServiceCall(
            domain = domain,
            service = HassApi.TURN_ON_SERVICE,
            hass_entity_id = parent_entity_id,
            service_data = { HassApi.COLOR_TEMP_KELVIN_ATTR: kelvin },
        )

    @classmethod
    def for_hs_color(
            cls,
            domain           : str,
            parent_entity_id : str,
            hue              : float,
            saturation       : float,
    ) -> HassServiceCall:
        return HassServiceCall(
            domain = domain,
            service = HassApi.TURN_ON_SERVICE,
            hass_entity_id = parent_entity_id,
            service_data = { HassApi.HS_COLOR_ATTR: [ hue, saturation ] },
        )
