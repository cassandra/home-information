import time
from .constants import (
    VIEW_MODE_HELP_SESSION_KEY,
    VIEW_MODE_HELP_DURATION_SECONDS,
    EDIT_MODE_HELP_SESSION_KEY,
    EDIT_MODE_HELP_DURATION_SECONDS,
    EDIT_MODE_ENTRY_COUNT_KEY,
)


def mark_profile_initialized(request):
    """Called when a profile is initialized to start view mode help timer."""
    request.session[VIEW_MODE_HELP_SESSION_KEY] = time.time()


def mark_edit_mode_entry(request):
    """
    Called when entering edit mode. 
    Only tracks if this is the same session that initialized the profile.
    """
    # Only track edit mode in the initialization session
    if VIEW_MODE_HELP_SESSION_KEY not in request.session:
        return
    
    # Increment entry count
    count = request.session.get(EDIT_MODE_ENTRY_COUNT_KEY, 0)
    
    # On first entry, start the help timer
    if count == 0:
        request.session[EDIT_MODE_HELP_SESSION_KEY] = time.time()
    
    request.session[EDIT_MODE_ENTRY_COUNT_KEY] = count + 1


def should_show_view_mode_help(request):
    """Check if view mode help should be shown based on session timing."""
    timestamp = request.session.get(VIEW_MODE_HELP_SESSION_KEY)
    if not timestamp:
        return False
    
    return (time.time() - timestamp) < VIEW_MODE_HELP_DURATION_SECONDS


def should_show_edit_mode_help(request):
    """
    Check if edit mode help should be shown.
    Only shows if:
    1. We're in the same session that initialized the profile
    2. This is the first edit mode entry
    3. We're still within the time window
    """
    # Must be in initialization session
    if VIEW_MODE_HELP_SESSION_KEY not in request.session:
        return False
    
    # Must have entered edit mode at least once
    timestamp = request.session.get(EDIT_MODE_HELP_SESSION_KEY)
    if not timestamp:
        return False
    
    # Must be within time window
    return (time.time() - timestamp) < EDIT_MODE_HELP_DURATION_SECONDS