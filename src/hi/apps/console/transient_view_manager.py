import logging
from typing import Optional

from hi.apps.common.singleton import Singleton

from .transient_models import TransientViewSuggestion
from .console_helper import ConsoleSettingsHelper

logger = logging.getLogger(__name__)


class TransientViewManager(Singleton):
    """
    Singleton class managing view change suggestions from various modules.
    Stores current suggestion in memory with metadata and provides API for modules to suggest view changes.
    """
    
    def __init_singleton__(self):
        self._current_suggestion: Optional[TransientViewSuggestion] = None
        logger.debug("TransientViewManager initialized")
        
    def suggest_view_change(self, url: str, duration_seconds: int,
                            priority: int = 0, trigger_reason: str = ""):
        """
        Register a suggestion for transient view change.
        
        Args:
            url: The URL to navigate to (must point to a view that subclasses HiGridView)
            duration_seconds: How long to show the view before reverting
            priority: Priority level (higher numbers = higher priority)
            trigger_reason: Description of what triggered this suggestion
        """
        suggestion = TransientViewSuggestion(
            url=url,
            duration_seconds=duration_seconds,
            priority=priority,
            trigger_reason=trigger_reason
        )
        
        # Only replace current suggestion if new one has higher priority
        # or if there's no current suggestion
        if (self._current_suggestion is None
                or suggestion.priority >= self._current_suggestion.priority):
            self._current_suggestion = suggestion
            logger.info(f"New transient view suggestion: {url} for {duration_seconds}s "
                        f"(reason: {trigger_reason}, priority: {priority})")
        else:
            logger.debug(f"Ignoring lower priority suggestion: {url} "
                         f"(priority {priority} vs current {self._current_suggestion.priority})")
        
    def get_current_suggestion(self) -> Optional[TransientViewSuggestion]:
        """
        Get and clear current suggestion.
        
        Returns:
            Current suggestion if one exists, None otherwise.
            The suggestion is cleared after being retrieved.
        """
        suggestion = self._current_suggestion
        if suggestion:
            logger.debug(f"Retrieving and clearing suggestion: {suggestion.url}")
        self._current_suggestion = None
        return suggestion
        
    def clear_suggestion(self):
        """Clear current suggestion without returning it."""
        if self._current_suggestion:
            logger.debug(f"Clearing suggestion: {self._current_suggestion.url}")
        self._current_suggestion = None
        
    def has_suggestion(self) -> bool:
        """Check if there's a current suggestion."""
        return self._current_suggestion is not None
        
    def peek_current_suggestion(self) -> Optional[TransientViewSuggestion]:
        """
        Get current suggestion without clearing it.
        
        Returns:
            Current suggestion if one exists, None otherwise.
            The suggestion is NOT cleared.
        """
        return self._current_suggestion
    
    def consider_alert_for_auto_view(self, alert):
        """
        Evaluate whether the given alert should trigger an auto-view suggestion.
        
        This is the main entry point for auto-view decision making.
        It encapsulates all the business logic about when and how to suggest
        view changes based on alerts.
        
        Args:
            alert: The Alert object to evaluate
        """
        # Check if auto-view is enabled in user settings
        if not self._is_auto_view_enabled():
            logger.debug("Auto-view is disabled in settings")
            return
            
        # Check if this alert should trigger auto-view
        if not self._should_alert_trigger_auto_view(alert):
            logger.debug(f"Alert {alert.signature} should not trigger auto-view")
            return
            
        # Try to get a view URL for this alert
        view_url = alert.get_view_url()
        if not view_url:
            logger.debug(f"No view URL available for alert {alert.signature}")
            return
            
        # Create the suggestion
        console_helper = ConsoleSettingsHelper()
        duration_seconds = console_helper.get_auto_view_duration()
        priority = alert.alert_priority  # Use the alert's priority
        
        self.suggest_view_change(
            url=view_url,
            duration_seconds=duration_seconds,
            priority=priority,
            trigger_reason=f"{alert.alarm_source.name.lower()}_alert"
        )
        
        logger.info(f"Created auto-view suggestion for alert {alert.signature}")
    
    def _is_auto_view_enabled(self) -> bool:
        """Check if auto-view switching is enabled in console settings."""
        console_helper = ConsoleSettingsHelper()
        return console_helper.get_auto_view_enabled()
    
    def _should_alert_trigger_auto_view(self, alert) -> bool:
        """
        Determine if an alert should trigger auto-view suggestion.
        
        By design, any alert that reaches this point has already been filtered
        by the event subsystem according to user-defined rules. Therefore, we 
        consider all alerts as candidates for auto-view switching, subject only
        to configuration settings and having a valid view URL.
        
        Args:
            alert: The Alert object to evaluate
            
        Returns:
            True if this alert should trigger auto-view, False otherwise
        """
        # All alerts that reach this point are considered valid for auto-view
        # The event subsystem has already done the filtering based on user rules
        # We just need to verify the alert has the necessary data
        
        first_alarm = alert.first_alarm
        if not first_alarm:
            logger.debug("Alert has no first_alarm, cannot trigger auto-view")
            return False
            
        # Any alert with proper alarm data can trigger auto-view
        # The actual view URL availability will be checked separately
        logger.debug(f"Alert {alert.signature} is eligible for auto-view")
        return True
