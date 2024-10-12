from hi.apps.common.enums import LabeledEnum


class IntegrationType(LabeledEnum):

    NONE              = ( 'None', 'No integration.' )
    ZONEMINDER        = ( 'ZoneMinder', 'ZoneMinder camera streaming and motion detection.' )
    HASS              = ( 'Home Assistant (hass)', 'Home Assistant device access' )

    @property
    def allow_entity_deletion(self) -> bool:
        return bool( self == IntegrationType.NONE )
    
