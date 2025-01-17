from enum import Enum
from typing import Tuple


class ZmMonitorFunction( Enum ):

    NONE           = 'None'
    MONITOR        = 'Monitor'
    MOTION_DETECT  = 'Modect' 
    RECORD         = 'Record' 
    MOTION_RECORD  = 'Mocord' 
    NO_DETECT      = 'Nodect' 

    def __str__(self):
        return self.value

    @classmethod
    def default_value(cls) -> str:
        return str(cls.MOTION_DETECT)
    
    @classmethod
    def choices(cls) -> Tuple[ str, str ]:
        choice_list = list()
        for enum in cls:
            choice_list.append( ( str(enum), str(enum) ) )
            continue
        return choice_list

    @classmethod
    def from_value( cls, target_value : str ):
        if target_value:
            for enum in cls:
                if enum.value.lower() == target_value.strip().lower():
                    return enum
                continue
        raise ValueError( f'Unknown value "{target_value}" for {cls.__name__}' )
    
    
class ZmRunStateType( Enum ):
    # TODO: Make these editable. ZM allows these to be user-defined.
    # Changing affects the monitor function state(s), so it is non-trivial
    # to add this to the simulator. Deferring this work until there more
    # need for this.
    
    STOP      = 'Stop'
    RESTART   = 'Restart'
    DEFAULT   = 'default'
    AWAY      = 'Away'
    HOME_DAY  = 'HomeDay'
    DISABLED  = 'Disabled'
    
    def __str__(self):
        return self.value

    @classmethod
    def default_value(cls) -> str:
        return str(cls.AWAY)
    
    @property
    def name(self):
        return self.value
    
    @classmethod
    def choices(cls) -> Tuple[ str, str ]:
        choice_list = list()
        for enum in cls:
            choice_list.append( ( str(enum), str(enum) ) )
            continue
        return choice_list

    @classmethod
    def from_value( cls, target_value : str ):
        if target_value:
            for enum in cls:
                if enum.value.lower() == target_value.strip().lower():
                    return enum
                continue
        raise ValueError( f'Unknown value "{target_value}" for {cls.__name__}' )
    
