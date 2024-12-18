from dataclasses import dataclass
from typing import List, Tuple

from .enums import SecurityLevel, SecurityState, SecurityStateAction


@dataclass
class SecurityStatusData:

    current_security_state    : SecurityState
    current_security_level    : SecurityLevel
    current_action_label      : str            = None
    current_action_value      : str            = None

    def __post_init__(self):
        if not self.current_action_label:
            self.current_action_label = self.current_security_state.label
        return

    @property
    def security_state_action_choices(self) -> List[ Tuple[ str, str ]]:
        return SecurityStateAction.choices()
    
