from dataclasses import dataclass
from typing import List, Tuple

from .enums import SecurityLevel, SecurityState, SecurityStateAction


@dataclass
class SecurityStatusData:

    current_security_state         : SecurityState
    current_security_level         : SecurityLevel
    security_state_action_choices  : List[ Tuple[ str, str ]]  = None

    def __post_init__(self):
        self.security_state_action_choices = SecurityStateAction.choices()
        return
    
