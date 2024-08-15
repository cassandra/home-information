from hi.apps.common.enums import LabeledEnum


class ControlType(LabeledEnum):

    CONTINUOUS   = ( 'Continuous', '' )
    DISCRETE     = ( 'Dicrete', '' )

    
class ControlledAreaType(LabeledEnum):

    LIGHT        = ( 'Light', '' )
    IRRIGATION   = ( 'Irrigation', '' )
