from dataclasses import dataclass
from enum import Enum
from typing import Optional

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from django.templatetags.static import static
from django.utils.html import format_html_join
from django.utils.safestring import SafeString, mark_safe

from hi.constants import DIVID


class FileViewerKind( Enum ):
    """
    How the in-app file viewer presents a file. external_name is what
    file-viewer.js dispatches on and what names the viewer's content
    regions in panes/file_viewer.html. A plain Enum, not LabeledEnum:
    kinds are never shown to users.
    """
    IMAGE        = ( 'image', )
    PDF          = ( 'pdf', )
    VIDEO        = ( 'video', )
    AUDIO        = ( 'audio', )
    TEXT         = ( 'text', )
    UNSUPPORTED  = ( 'unsupported', )

    def __init__( self, external_name : str ):
        self.external_name = external_name
        return

    @classmethod
    def from_mime_type( cls, mime_type : Optional[ str ] ) -> 'FileViewerKind':
        # MIME types are case-insensitive and may carry parameters
        # (RFC 2045), e.g. "text/plain; charset=utf-8".
        normalized = ( mime_type or '' ).split( ';', 1 )[ 0 ].strip().lower()
        if normalized in _KIND_BY_MIME_TYPE:
            return _KIND_BY_MIME_TYPE[ normalized ]
        if normalized.startswith( _TEXT_TYPE_PREFIX ):
            return cls.TEXT
        return cls.UNSUPPORTED


# Only formats current browsers display. Others (e.g. HEIC photos, TIFF
# scans, QuickTime video) would fail to load in the viewer, so they get
# "No preview available" and the open-in-new-tab link instead.
_KIND_BY_MIME_TYPE = {
    'application/pdf'  : FileViewerKind.PDF,
    'image/avif'       : FileViewerKind.IMAGE,
    'image/bmp'        : FileViewerKind.IMAGE,
    'image/gif'        : FileViewerKind.IMAGE,
    'image/jpeg'       : FileViewerKind.IMAGE,
    'image/png'        : FileViewerKind.IMAGE,
    'image/svg+xml'    : FileViewerKind.IMAGE,
    'image/webp'       : FileViewerKind.IMAGE,
    'video/mp4'        : FileViewerKind.VIDEO,
    'video/ogg'        : FileViewerKind.VIDEO,
    'video/webm'       : FileViewerKind.VIDEO,
    'audio/aac'        : FileViewerKind.AUDIO,
    'audio/flac'       : FileViewerKind.AUDIO,
    'audio/mp4'        : FileViewerKind.AUDIO,
    'audio/mpeg'       : FileViewerKind.AUDIO,
    'audio/ogg'        : FileViewerKind.AUDIO,
    'audio/wav'        : FileViewerKind.AUDIO,
    'audio/webm'       : FileViewerKind.AUDIO,
    'audio/x-wav'      : FileViewerKind.AUDIO,
    'application/json' : FileViewerKind.TEXT,
    'application/xml'  : FileViewerKind.TEXT,
}

# Any text type reads as plain text (shown with textContent).
_TEXT_TYPE_PREFIX = 'text/'


@dataclass( frozen = True )
class FileViewerItem:
    """
    An app-served file to show in the in-app file viewer. Each source of
    files (attributes, integration attachments) builds one from itself.
    Details not known for a file are None, and the viewer leaves them
    out of its display.
    """
    url         : str
    mime_type   : Optional[ str ]  = None
    title       : Optional[ str ]  = None
    filename    : Optional[ str ]  = None
    size_bytes  : Optional[ int ]  = None


def file_viewer_attrs( item : Optional[ FileViewerItem ] ) -> SafeString:
    """
    Attributes that make a button open the item in the in-app file
    viewer (see file-viewer.js). Without an item (e.g. a file attribute
    whose file was never stored) the button is disabled.
    """
    if item is None:
        return mark_safe( 'disabled' )
    if not item.url:
        # A trigger without a file would open an empty viewer.
        raise ValueError( 'A file viewer trigger needs a file URL' )
    kind = FileViewerKind.from_mime_type( item.mime_type )
    size_text = filesizeformat( item.size_bytes ) if item.size_bytes is not None else None
    attr_values = (
        ( DIVID['FILE_VIEWER_URL_ATTR'], item.url ),
        ( DIVID['FILE_VIEWER_KIND_ATTR'], kind.external_name ),
        ( DIVID['FILE_VIEWER_TITLE_ATTR'], item.title or item.filename ),
        ( DIVID['FILE_VIEWER_FILENAME_ATTR'], item.filename ),
        ( DIVID['FILE_VIEWER_MIME_TYPE_ATTR'], item.mime_type ),
        ( DIVID['FILE_VIEWER_SIZE_ATTR'], size_text ),
    )
    return format_html_join(
        ' ',
        '{}="{}"',
        ( ( name, value ) for name, value in attr_values if value ),
    )


@dataclass( frozen = True )
class PdfJsAssets:
    """
    URLs of the vendored pdf.js (legacy build) that the file viewer
    loads on first use. Resource URLs are directories: pdf.js appends
    file names to them, so they bypass the static manifest, which keeps
    unhashed copies of every file.
    """
    library_url              : str
    worker_url               : str
    wasm_url                 : str
    standard_font_data_url   : str
    icc_url                  : str

    STATIC_DIRECTORY = 'pdfjs-6.5.438'

    @classmethod
    def from_static( cls ) -> 'PdfJsAssets':
        directory = cls.STATIC_DIRECTORY
        resource_base_url = f'{settings.STATIC_URL}{directory}'
        return cls(
            library_url = static( f'{directory}/build/pdf.min.mjs' ),
            worker_url = static( f'{directory}/build/pdf.worker.min.mjs' ),
            wasm_url = f'{resource_base_url}/wasm/',
            standard_font_data_url = f'{resource_base_url}/standard_fonts/',
            icc_url = f'{resource_base_url}/iccs/',
        )
