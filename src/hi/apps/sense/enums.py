from hi.apps.common.enums import LabeledEnum


class SensorType(LabeledEnum):

    DEFAULT              = ( 'Default', '' )  # EntityState will define behavior


class CorrelationRole(LabeledEnum):
    """
    Role of a sensor response in a correlated event sequence.
    Used to identify start and end events that belong to the same logical event.
    """

    START                = ( 'Start', 'Event start/beginning' )
    END                  = ( 'End', 'Event end/completion' )


