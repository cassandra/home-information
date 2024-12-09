from hi.apps.common.enums import LabeledEnum

    
class SecurityLevel( LabeledEnum ):
    """
    This defines the internal systrem security level for determing which
    alerts should be created.  The SecurityState and SecurtyStateActions
    control the transitions between security levels and how alerts will be
    handled.
    """
    
    HIGH      = ( 'High' , '' )
    LOW       = ( 'Low'  , '' )
    OFF       = ( 'Off'  , '' )

    @classmethod
    def non_off_choices(cls):
        choice_list = list()
        for security_level in cls:
            if security_level == SecurityLevel.OFF:
                continue
            choice_list.append( ( security_level.name.lower(), security_level.label ) )
            continue
        return choice_list
    
    
class SecurityState( LabeledEnum ):
    """
    This is the overall security level setting for security status monitoring
    that dictates what type of security events are relevant.
    """
    
    DISABLED      = ( 'Disabled' , '' )
    DAY           = ( 'Day'     , '' )
    NIGHT         = ( 'Night'    , '' )
    AWAY          = ( 'Away'     , '' )
    
    
class SecurityStateAction( LabeledEnum ):
    """
    This is the overall security level setting for security status monitoring
    that dictates what type of security events are relevant.
    """
    
    DISABLE       = ( 'Disable' , '' )
    DAY           = ( 'Day'     , '' )
    NIGHT         = ( 'Night'    , '' )
    AWAY          = ( 'Away'     , '' )
    SNOOZE        = ( 'Snooze'       , '' )
