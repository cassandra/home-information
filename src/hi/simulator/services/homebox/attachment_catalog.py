"""
Pre-canned HomeBox attachment templates for the simulator.

The real HomeBox API delivers attachments as binary payloads (images,
PDFs) tied to inventory items. To exercise the HI app's attachment
download / parse / store paths without introducing actual file
management on the simulator side, this module defines a small fixed
catalog of templates as a ``LabeledEnum``; each item's
``attachment_keys`` field is a CSV of those members' wire keys.

The bytes are rendered on demand by the download endpoint (no files
on disk, no upload UI). Each rendered artifact carries the item name
in its content so the operator can recognize which item an
attachment came from when inspecting it inside HI.

Wire convention follows ``LabeledEnum``: a member's wire key is
``member.name.lower()`` (e.g., ``AttachmentTemplate.MANUAL`` →
``"manual"``). That is the string used in URLs, in the per-item
``attachment_keys`` CSV, and as the ``id`` field on the API
attachment dict.
"""
import logging
from typing import Dict, List, Optional, Tuple

from hi.apps.common.enums import LabeledEnum

from hi.simulator.media import (
    render_placeholder_image,
    render_placeholder_pdf,
)

logger = logging.getLogger(__name__)


# Thumbnail rendering scale: real HomeBox thumbnails are scaled-down
# originals at the source aspect, not reformatted. The simulator
# follows the same shape.
_THUMBNAIL_SCALE = 0.75


class AttachmentTemplate( LabeledEnum ):
    """Catalog of pre-canned attachment templates.

    Each member carries the user-facing label, MIME type, rendering
    kind, and source pixel dimensions. The wire key (used in URLs,
    CSV fields, and the API ``attachment.id`` value) is
    ``member.name.lower()`` per the ``LabeledEnum`` convention.
    ``description`` is left empty — operator-facing label is
    sufficient for the picker UI.

    Photo variants (``PHOTO_SQUARE`` / ``PHOTO_WIDE`` /
    ``PHOTO_WIDE_X`` / ``PHOTO_TALL`` / ``PHOTO_TALL_X``) exist so
    the operator can exercise the HI app's thumbnail grid across
    different image aspect ratios without uploading real files.
    """

    RECEIPT = ('Receipt', '', 'image/png', 'image', (320, 240))
    MANUAL = ('Manual', '', 'application/pdf', 'pdf', (320, 240))
    PHOTO = ('Photo', '', 'image/jpeg', 'image', (320, 240))
    WARRANTY = ('Warranty', '', 'application/pdf', 'pdf', (320, 240))
    PHOTO_SQUARE = ('Photo (Square)', '', 'image/jpeg', 'image', (320, 320))
    PHOTO_WIDE = ('Photo (Wide)', '', 'image/jpeg', 'image', (320, 180))
    PHOTO_WIDE_X = ('Photo (Ultra Wide)', '', 'image/jpeg', 'image', (640, 180))
    PHOTO_TALL = ('Photo (Tall)', '', 'image/jpeg', 'image', (180, 320))
    PHOTO_TALL_X = ('Photo (Ultra Tall)', '', 'image/jpeg', 'image', (180, 640))

    def __init__( self,
                  label       : str,
                  description : str,
                  mime_type   : str,
                  kind        : str,
                  source_size : Tuple[ int, int ] ):
        super().__init__( label, description )
        self.mime_type = mime_type
        self.kind = kind
        self.source_size = source_size
        return

    @property
    def key( self ) -> str:
        """Wire string used in URLs, CSV fields, and the API
        ``attachment.id`` value. Stable across renames as long as
        the enum member name is preserved."""
        return self.name.lower()

    @property
    def thumbnail_size( self ) -> Tuple[ int, int ]:
        width, height = self.source_size
        return ( int( width * _THUMBNAIL_SCALE ), int( height * _THUMBNAIL_SCALE ) )


def attachment_choices() -> List[ Tuple[ str, str ] ]:
    """Choice tuples (value, label) for any UI that needs to render a
    selector over the catalog. Single source of truth — the
    ``SimEntityFieldsForm`` builder reads this via the
    ``csv_choices`` field-metadata hook so renaming a member here
    updates the picker without separate coordination."""
    return [
        ( template.key, f'{template.label} ({template.mime_type})' )
        for template in AttachmentTemplate
    ]


def parse_attachment_keys( csv_value: str ) -> List[ AttachmentTemplate ]:
    """Split the CSV ``attachment_keys`` field into validated
    templates. Unknown keys are dropped silently (with a debug log)
    — the field is operator-edited free text and a typo should not
    500 the simulator's item endpoint."""
    if not csv_value:
        return []
    templates = []
    for raw in csv_value.split( ',' ):
        key = raw.strip().lower()
        if not key:
            continue
        try:
            template = AttachmentTemplate.from_name( key )
        except ValueError:
            logger.debug( f'Ignoring unknown attachment key "{key}"' )
            continue
        templates.append( template )
    return templates


def build_attachment_metadata( template: AttachmentTemplate ) -> Dict[ str, object ]:
    """The dict shape the real HomeBox API emits inside an item's
    ``attachments`` array. For image-kind templates also emits a
    ``thumbnail`` sub-dict so the integration's thumbnail proxy path
    can be exercised; PDF templates have no thumbnail entry."""
    metadata: Dict[ str, object ] = {
        'id'       : template.key,
        'title'    : template.label,
        'mimeType' : template.mime_type,
    }
    if template.kind == 'image':
        metadata['thumbnail'] = { 'id': f'{template.key}-thumb' }
    return metadata


def render_attachment_content( template  : AttachmentTemplate,
                               item_name : str,
                               thumbnail : bool = False,
                               ) -> Optional[ Dict[ str, object ] ]:
    """Generate the binary payload for the given catalog template,
    with ``item_name`` baked into the content so the operator can
    distinguish artifacts in the HI UI. When ``thumbnail`` is True
    and the template is image-kind, the image is rendered at a
    smaller size at the same source aspect; ``thumbnail=True`` with
    a non-image template returns None. Returns a dict with
    ``content`` (bytes) and ``mime_type`` (str), or None if the
    template's ``kind`` is unrecognized or unsupported for the
    requested variant."""
    if template.kind == 'image':
        image_format = 'PNG' if template.mime_type == 'image/png' else 'JPEG'
        size = template.thumbnail_size if thumbnail else template.source_size
        content = render_placeholder_image(
            text_lines = [ template.label, item_name, '(simulator)' ],
            image_format = image_format,
            size = size,
        )
    elif template.kind == 'pdf':
        if thumbnail:
            return None
        content = render_placeholder_pdf(
            text_lines = [ f'{template.label}: {item_name} (simulator)' ],
        )
    else:
        return None
    return {
        'content'   : content,
        'mime_type' : template.mime_type,
    }
