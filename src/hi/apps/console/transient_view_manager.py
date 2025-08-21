import logging
from typing import Optional

from hi.apps.common.singleton import Singleton

from .transient_models import TransientViewSuggestion

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
            url: The URL to navigate to
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
