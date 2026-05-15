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
import io
import logging
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from hi.apps.common.enums import LabeledEnum

logger = logging.getLogger(__name__)


class AttachmentTemplate( LabeledEnum ):
    """Catalog of pre-canned attachment templates.

    Each member carries the user-facing label, MIME type, and
    rendering kind. The wire key (used in URLs, CSV fields, and the
    API ``attachment.id`` value) is ``member.name.lower()`` per the
    ``LabeledEnum`` convention. ``description`` is left empty —
    operator-facing label is sufficient for the picker UI.
    """

    RECEIPT  = ( 'Receipt'  , '' , 'image/png'        , 'image' )
    MANUAL   = ( 'Manual'   , '' , 'application/pdf'  , 'pdf'   )
    PHOTO    = ( 'Photo'    , '' , 'image/jpeg'       , 'image' )
    WARRANTY = ( 'Warranty' , '' , 'application/pdf'  , 'pdf'   )

    def __init__( self,
                  label       : str,
                  description : str,
                  mime_type   : str,
                  kind        : str ):
        super().__init__( label, description )
        self.mime_type = mime_type
        self.kind = kind
        return

    @property
    def key( self ) -> str:
        """Wire string used in URLs, CSV fields, and the API
        ``attachment.id`` value. Stable across renames as long as
        the enum member name is preserved."""
        return self.name.lower()


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


def build_attachment_metadata( template: AttachmentTemplate ) -> Dict[ str, str ]:
    """The dict shape the real HomeBox API emits inside an item's
    ``attachments`` array. Returned shape is intentionally small —
    the HI integration's HbItem parser reads ``id`` (used as the
    download key here), ``title``, and ``mimeType``."""
    return {
        'id'       : template.key,
        'title'    : template.label,
        'mimeType' : template.mime_type,
    }


def render_attachment_content( template  : AttachmentTemplate,
                               item_name : str,
                               ) -> Optional[ Dict[ str, object ] ]:
    """Generate the binary payload for the given catalog template,
    with ``item_name`` baked into the content so the operator can
    distinguish artifacts in the HI UI. Returns a dict with
    ``content`` (bytes) and ``mime_type`` (str), or None if the
    template's ``kind`` is unrecognized (should not happen with
    the current catalog)."""
    if template.kind == 'image':
        content = _render_image(
            title = template.label,
            item_name = item_name,
            image_format = 'PNG' if template.mime_type == 'image/png' else 'JPEG',
        )
    elif template.kind == 'pdf':
        content = _render_pdf( title = template.label, item_name = item_name )
    else:
        return None
    return {
        'content'   : content,
        'mime_type' : template.mime_type,
    }


def _render_image( title : str, item_name : str, image_format : str ) -> bytes:
    """Pillow-rendered placeholder image: a colored canvas with the
    attachment title and item name drawn on it. Default bitmap font
    keeps the simulator independent of system font availability."""
    image = Image.new( mode = 'RGB', size = ( 320, 160 ), color = ( 230, 240, 250 ) )
    draw = ImageDraw.Draw( image )
    draw.text( ( 20, 30 ), title, fill = ( 30, 40, 80 ) )
    draw.text( ( 20, 70 ), item_name, fill = ( 30, 40, 80 ) )
    draw.text( ( 20, 110 ), '(simulator)', fill = ( 90, 90, 90 ) )
    buffer = io.BytesIO()
    image.save( buffer, format = image_format )
    return buffer.getvalue()


def _render_pdf( title : str, item_name : str ) -> bytes:
    """Hand-rolled minimal single-page PDF. The PDF format is a mix
    of structured text and a binary xref table; we build the body
    first, then compute byte offsets for the xref. This avoids
    pulling in an external PDF library for what amounts to four
    objects of placeholder content. The output is a valid PDF that
    most viewers will render with the title and item-name text."""
    text = f'{title}: {item_name} (simulator)'
    # Escape parens that would otherwise terminate a PDF string literal.
    text_safe = text.replace( '\\', '\\\\' ).replace( '(', '\\(' ).replace( ')', '\\)' )
    content_stream = (
        f'BT /F1 18 Tf 60 740 Td ({text_safe}) Tj ET'
    ).encode( 'latin-1' )

    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        (
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            b'/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>'
        ),
        b'<< /Length ' + str( len( content_stream ) ).encode( 'latin-1' )
        + b' >>\nstream\n' + content_stream + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]

    output = bytearray( b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n' )
    offsets = []
    for index, body in enumerate( objects, start = 1 ):
        offsets.append( len( output ) )
        output += f'{index} 0 obj\n'.encode( 'latin-1' )
        output += body
        output += b'\nendobj\n'

    xref_offset = len( output )
    output += f'xref\n0 {len(objects) + 1}\n'.encode( 'latin-1' )
    output += b'0000000000 65535 f \n'
    for offset in offsets:
        output += f'{offset:010d} 00000 n \n'.encode( 'latin-1' )
    output += (
        f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
        f'startxref\n{xref_offset}\n%%EOF\n'
    ).encode( 'latin-1' )
    return bytes( output )
