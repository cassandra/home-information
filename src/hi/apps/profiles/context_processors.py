from .session_helpers import (
    should_show_view_mode_help,
    should_show_edit_mode_help,
)


def profiles_context(request):
    """Provide profile-related context variables for templates."""
    return {
        'show_view_mode_help': should_show_view_mode_help(request),
        'show_edit_mode_help': should_show_edit_mode_help(request),
    }
