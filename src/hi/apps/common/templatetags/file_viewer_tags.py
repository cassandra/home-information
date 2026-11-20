from typing import Optional

from django import template
from django.utils.safestring import SafeString

from hi.apps.common import file_viewer
from hi.apps.common.file_viewer import FileViewerKind, PdfJsAssets
from hi.constants import DIVID

register = template.Library()


@register.simple_tag
def file_viewer_attrs( url         : str,
                       mime_type   : Optional[ str ] = None,
                       title       : Optional[ str ] = None,
                       filename    : Optional[ str ] = None,
                       size_bytes  : Optional[ int ] = None ) -> SafeString:
    """
    Usage: {% file_viewer_attrs url=... mime_type=... title=... filename=... size_bytes=... %}
    on a <button type="button">. Only url is required.
    """
    return file_viewer.file_viewer_attrs(
        url = url,
        mime_type = mime_type,
        title = title,
        filename = filename,
        size_bytes = size_bytes,
    )


@register.inclusion_tag( 'panes/file_viewer.html' )
def file_viewer_shell() -> dict:
    """ The viewer overlay, rendered once per page (see pages/base.html). """
    return {
        'DIVID': DIVID,
        # A dict, since templates call a class (the enum) instead of
        # looking up its members.
        'kind': { kind.name: kind.external_name for kind in FileViewerKind },
        'pdfjs': PdfJsAssets.from_static(),
    }
