from django import template
from django.utils.safestring import SafeString

from hi.apps.common import file_viewer
from hi.apps.common.file_viewer import FileViewerItem, FileViewerKind, PdfJsAssets
from hi.constants import DIVID

register = template.Library()


@register.simple_tag
def file_viewer_attrs( item : FileViewerItem ) -> SafeString:
    """
    Usage: {% file_viewer_attrs attribute.file_viewer_item %} on a
    <button type="button">.
    """
    return file_viewer.file_viewer_attrs( item = item )


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
