from dataclasses import dataclass
from enum import Enum
from typing import Optional

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from django.templatetags.static import static
from django.utils.html import format_html_join
from django.utils.safestring import SafeString

from hi.constants import DIVID


class FileViewerKind( Enum ):
    """
    How the in-app file viewer presents a file. external_name is what
    file-viewer.js dispatches on and what names the viewer's content
    regions in panes/file_viewer.html.
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
        # MIME types are case-insensitive (RFC 2045).
        normalized = ( mime_type or '' ).strip().lower()
        if normalized in _KIND_BY_MIME_TYPE:
            return _KIND_BY_MIME_TYPE[ normalized ]
        top_level_type = normalized.split( '/', 1 )[ 0 ]
        return _KIND_BY_TOP_LEVEL_TYPE.get( top_level_type, cls.UNSUPPORTED )


_KIND_BY_MIME_TYPE = {
    'application/pdf': FileViewerKind.PDF,
}

_KIND_BY_TOP_LEVEL_TYPE = {
    'image': FileViewerKind.IMAGE,
    'video': FileViewerKind.VIDEO,
    'audio': FileViewerKind.AUDIO,
    'text': FileViewerKind.TEXT,
}


def file_viewer_attrs( url         : str,
                       mime_type   : Optional[ str ] = None,
                       title       : Optional[ str ] = None,
                       filename    : Optional[ str ] = None,
                       size_bytes  : Optional[ int ] = None ) -> SafeString:
    """
    Attributes that make an element open the given app-served file in
    the in-app file viewer (see file-viewer.js). Details not known for
    a file are omitted, and the viewer leaves them out of its display.
    """
    if not url:
        # A trigger without a file would open an empty viewer.
        raise ValueError( 'A file viewer trigger needs a file URL' )
    kind = FileViewerKind.from_mime_type( mime_type )
    size_text = filesizeformat( size_bytes ) if size_bytes is not None else None
    attr_values = (
        ( DIVID['FILE_VIEWER_URL_ATTR'], url ),
        ( DIVID['FILE_VIEWER_KIND_ATTR'], kind.external_name ),
        ( DIVID['FILE_VIEWER_TITLE_ATTR'], title or filename ),
        ( DIVID['FILE_VIEWER_FILENAME_ATTR'], filename ),
        ( DIVID['FILE_VIEWER_MIME_TYPE_ATTR'], mime_type ),
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
