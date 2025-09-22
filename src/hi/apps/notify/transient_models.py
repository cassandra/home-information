from dataclasses import dataclass
from typing import List
    
    
@dataclass
class NotificationItem:
    signature     : str
    title         : str
    source_obj    : object  = None
    

@dataclass
class Notification:
    title         : str
    item_list     : List[ NotificationItem ]


@dataclass
class NotificationMaintenanceResult:
    """Result of a periodic maintenance execution."""
    notifications_found: int = 0
    notifications_sent: int = 0
    notifications_skipped: int = 0  # Skipped due to no email addresses
    notifications_failed: int = 0
    notifications_disabled: bool = False
    no_email_addresses: bool = False
    error_messages: List[str] = None

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []

    def get_summary_message(self) -> str:
        """Generate a human-readable summary message for health status."""
        if self.notifications_disabled:
            return "Notifications disabled"

        if self.notifications_found == 0:
            return "No notifications found"

        if self.no_email_addresses:
            return f"No email addresses configured ({self.notifications_found} notification{'s' if self.notifications_found != 1 else ''} pending)"

        # Build the message parts
        parts = []

        if self.notifications_sent > 0:
            parts.append(
                f"Sent {self.notifications_sent} notification{'s' if self.notifications_sent != 1 else ''}")

        if self.notifications_skipped > 0:
            parts.append(f"{self.notifications_skipped} skipped (no addresses)")

        if self.notifications_failed > 0:
            parts.append(f"{self.notifications_failed} failed")

        if not parts:
            return "No notifications sent"

        return ", ".join(parts)


    
