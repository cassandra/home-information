from django.shortcuts import render
from django.views.generic import View

from hi.apps.common.templatetags.icons import AVAILABLE_ICONS, ICON_SIZES, ICON_COLORS


class TestUiCommonHomeView(View):
    """Home view for common app UI testing."""
    
    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, "common/tests/ui/home.html", context)


class TestUiIconBrowserView(View):
    """
    Auto-discovery view for browsing all available icons.
    Automatically displays any new icons added to the system without manual updates.
    """
    
    def get(self, request, *args, **kwargs):
        # Get all available icons from the icon system
        available_icons = sorted(AVAILABLE_ICONS)
        available_sizes = sorted(ICON_SIZES)
        available_colors = sorted(ICON_COLORS)
        
        context = {
            'available_icons': available_icons,
            'available_sizes': available_sizes, 
            'available_colors': available_colors,
            'total_icons': len(available_icons)
        }
        return render(request, "common/tests/ui/icon_browser.html", context)
    
