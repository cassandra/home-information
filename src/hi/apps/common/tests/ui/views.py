import os

from django.contrib.staticfiles import finders
from django.shortcuts import render
from django.templatetags.static import static
from django.views.generic import View

from hi.apps.common.file_viewer import FileViewerItem
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


class TestUiFileViewerView(View):
    """
    Opens each kind of file in the in-app file viewer, from the page and
    from inside a Bootstrap modal. Samples are static test files, plus
    a missing file and a file that is not the PDF it claims to be for
    the error state, and a file with no details.
    """

    SAMPLE_DIRECTORY = 'tests/file_viewer'

    SAMPLE_FILES = (
        ( 'Landscape image', 'landscape.png', 'image/png' ),
        ( 'Tall image', 'tall.png', 'image/png' ),
        ( 'Video clip', 'clip.mp4', 'video/mp4' ),
        ( 'Audio tone', 'tone.wav', 'audio/wav' ),
        ( 'Text notes', 'notes.txt', 'text/plain' ),
        ( 'PDF manual', 'manual.pdf', 'application/pdf' ),
        ( 'Binary file', 'firmware.bin', 'application/octet-stream' ),
    )

    def get(self, request, *args, **kwargs):
        samples = [
            self._static_sample( title = title, filename = filename, mime_type = mime_type )
            for title, filename, mime_type in self.SAMPLE_FILES
        ]
        samples.append( FileViewerItem(
            title = 'Missing image (error)',
            url = static( f'{self.SAMPLE_DIRECTORY}/does-not-exist.png' ),
            mime_type = 'image/png',
            filename = 'does-not-exist.png',
        ))
        samples.append( FileViewerItem(
            title = 'Broken PDF (error)',
            url = static( f'{self.SAMPLE_DIRECTORY}/notes.txt' ),
            mime_type = 'application/pdf',
            filename = 'not-really.pdf',
        ))
        samples.append( FileViewerItem(
            title = 'Unknown details',
            url = static( f'{self.SAMPLE_DIRECTORY}/firmware.bin' ),
            mime_type = None,
        ))
        context = {
            'samples': samples,
        }
        return render(request, "common/tests/ui/file_viewer.html", context)

    def _static_sample( self,
                        title      : str,
                        filename   : str,
                        mime_type  : str ) -> FileViewerItem:
        path = f'{self.SAMPLE_DIRECTORY}/{filename}'
        file_path = finders.find( path )
        return FileViewerItem(
            title = title,
            url = static( path ),
            mime_type = mime_type,
            filename = filename,
            size_bytes = os.path.getsize( file_path ) if file_path else None,
        )
