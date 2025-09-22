from dataclasses import dataclass


@dataclass
class AlertQueueCleanupResult:

    expired_removed       : int  = 0
    acknowledged_removed  : int  = 0
    total_removed         : int  = 0
    

@dataclass
class AlertMaintenanceResult:

    alerts_before_cleanup: int = 0
    alerts_after_cleanup: int = 0
    expired_alerts_removed: int = 0
    acknowledged_alerts_removed: int = 0
    error_message: str = None

    @property
    def total_alerts_removed(self) -> int:
        return self.expired_alerts_removed + self.acknowledged_alerts_removed

    def get_summary_message(self) -> str:
        if self.error_message:
            return f"Alert maintenance failed: {self.error_message}"

        if self.alerts_before_cleanup == 0:
            return "No alerts in queue"

        if self.total_alerts_removed == 0:
            return f"No cleanup needed ({self.alerts_after_cleanup} active alert{'s' if self.alerts_after_cleanup != 1 else ''})"

        # Build removal details
        removal_parts = []
        if self.expired_alerts_removed > 0:
            removal_parts.append(f"{self.expired_alerts_removed} expired")
        if self.acknowledged_alerts_removed > 0:
            removal_parts.append(f"{self.acknowledged_alerts_removed} acknowledged")

        removal_text = ", ".join(removal_parts)
        active_text = f"{self.alerts_after_cleanup} active" if self.alerts_after_cleanup > 0 else "none active"

        return f"Removed {removal_text}, {active_text}"


    
