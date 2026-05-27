from hi.apps.common.enums import LabeledEnum


class EventType(LabeledEnum):

    SECURITY        = ( 'Security'     , '' )
    MAINTENANCE     = ( 'Maintenance'  , '' )
    INFORMATION     = ( 'Information'  , '' )
    AUTOMATION      = ( 'Automation'   , '' )


class EventClauseOperator(LabeledEnum):
    """How an EventClause compares the live wire value against its
    stored target value. EQ / NEQ match against a single discrete
    value; IN matches against a comma-separated list of values; the
    numeric operators trigger when a continuous reading crosses a
    threshold (battery < 20%, etc.). Numeric ops parse both sides
    via ``float()`` at match time and silently no-op on parse failure
    so a malformed wire value never raises into the matcher."""

    EQ  = ( 'Equals'       , 'Match when the value equals the target string.' )
    NEQ = ( 'Not Equals'   , 'Match when the value does not equal the target string.' )
    IN  = ( 'Is One Of'    , 'Match when the value matches any item in a comma-separated list.' )
    LT  = ( 'Less Than'    , 'Match when the numeric value drops below the threshold.' )
    LTE = ( 'At Most'      , 'Match when the numeric value is at or below the threshold.' )
    GT  = ( 'Greater Than' , 'Match when the numeric value rises above the threshold.' )
    GTE = ( 'At Least'     , 'Match when the numeric value is at or above the threshold.' )

    @classmethod
    def default(cls):
        return cls.EQ

    @property
    def is_numeric(self) -> bool:
        """Operators that compare numeric magnitudes. Form-time
        validation requires a parseable numeric value for these; the
        matcher silently no-ops on non-numeric runtime values."""
        return self in {
            EventClauseOperator.LT,
            EventClauseOperator.LTE,
            EventClauseOperator.GT,
            EventClauseOperator.GTE,
        }

