from hi.apps.common.enums import LabeledEnum


class AlarmLevel(LabeledEnum):
    
    NONE          = ( 'None'      , ''               , 0 )
    INFO          = ( 'Info'      , ''              , 10 )
    WARNING       = ( 'Warning'   , ''             , 100 )
    CRITICAL      = ( 'Critical'  , ''            , 1000 )

    def __init__( self,
                  label             : str,
                  description       : str,
                  priority          : int ):
        super().__init__( label, description )
        self.priority = priority
        return

    
class SecurityPosture(LabeledEnum):
    """
    This is the overall security level setting for security status monitoring
    that dictates what type of security events are relevant.
    """
    
    UNKNOWN   = ( 'Unknown'  , '' )
    DISABLED  = ( 'Disabled' , '' )
    HOME      = ( 'Home'     , '' )
    NIGHT     = ( 'Night'    , '' )
    AWAY      = ( 'Away'     , '' )
    ERROR     = ( 'Error'    , '' )


class AlertState(LabeledEnum):

    ERROR         = ( 'Error'           , ''   , -12 )
    UNKNOWN       = ( 'Unknown'         , ''    , -3 )
    DISABLED      = ( 'Disabled'        , ''    , -1 )
    ENABLED       = ( 'Enabled'         , ''     , 0 )
    IDLE          = ( 'Idle'            , ''     , 1 )
    INFO_RECENT   = ( 'Info (recent)'   , ''     , 9 )
    INFO          = ( 'Info'            , ''    , 10 )
    ALERT_RECENT  = ( 'Alert (recent)'  , ''    , 99 )
    ALERT         = ( 'Alert'           , ''   , 100 )
    ALARM_RECENT  = ( 'Alarm (recent)'  , ''   , 999 )
    ALARM         = ( 'Alarm'           , ''  , 1000 )

    def __init__( self,
                  label             : str,
                  description       : str,
                  priority          : int ):
        super().__init__( label, description )
        self.priority = priority
        return

    @staticmethod
    def get_recent_variant( cls, security_state : 'AlertState' ):
        """
        Converts a state to its 'recent' version if one exists.
        Otherwise, just returns the state passed in.
        """
        if security_state == cls.INFO:
            return cls.INFO_RECENT
        if security_state == cls.ALERT:
            return cls.ALERT_RECENT
        if security_state == cls.ALARM:
            return cls.ALARM_RECENT
        return security_state
