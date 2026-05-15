from hi.apps.common.enums import LabeledEnum


class EventType(LabeledEnum):

    SECURITY        = ( 'Security'     , '' )
    MAINTENANCE     = ( 'Maintenance'  , '' )
    INFORMATION     = ( 'Information'  , '' )
    AUTOMATION      = ( 'Automation'   , '' )


class EventClauseOperator(LabeledEnum):
    """How an EventClause compares the live wire value against its
    stored target value. EQ matches a discrete value (motion ACTIVE,
    smoke SMOKE_DETECTED, etc.); the numeric operators trigger when
    a continuous reading crosses a threshold (battery < 20%, etc.).
    Numeric ops parse both sides via ``float()`` at match time and
    silently no-op on parse failure so a malformed wire value never
    raises into the matcher."""

    EQ  = ( 'Equals'       , 'Trigger when the value equals the target string.' )
    LT  = ( 'Less Than'    , 'Trigger when the numeric value drops below the threshold.' )
    LTE = ( 'At Most'      , 'Trigger when the numeric value is at or below the threshold.' )
    GT  = ( 'Greater Than' , 'Trigger when the numeric value rises above the threshold.' )
    GTE = ( 'At Least'     , 'Trigger when the numeric value is at or above the threshold.' )

    @classmethod
    def default(cls):
        return cls.EQ

