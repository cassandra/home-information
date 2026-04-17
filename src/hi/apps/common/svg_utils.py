import logging
import os
import xml.etree.ElementTree as ET

from hi.apps.common.file_utils import generate_unique_filename
from hi.apps.common.svg_models import SvgViewBox

logger = logging.getLogger(__name__)

ET.register_namespace('', 'http://www.w3.org/2000/svg')

DANGEROUS_TAGS = {
    'script', 'foreignObject', 'iframe', 'object',
    'animation', 'audio', 'video', 'style',
}
DANGEROUS_ATTRS = {
    'onload', 'onclick', 'onmouseover',
}
HREF_ATTRS = {
    'href', 'xlink:href',
    '{http://www.w3.org/1999/xlink}href',
}


def process_svg_content( svg_content,
                         media_destination_directory,
                         source_filename,
                         remove_dangerous = True ):
    """
    Process a full SVG document: validate, extract viewBox, strip the
    outer <svg> wrapper, clean namespaces, scan for dangerous elements,
    and generate a unique MEDIA_ROOT filename.

    Args:
        svg_content: Full SVG content string with outer <svg> element.
        media_destination_directory: Relative directory in MEDIA_ROOT (e.g., 'location/svg').
        source_filename: Original filename for generating unique destination name.
        remove_dangerous: If True, silently remove dangerous elements.
                          If False, return counts but do not remove.

    Returns:
        dict with keys:
            'svg_fragment_content': Inner SVG content string (outer <svg> stripped).
            'svg_viewbox': SvgViewBox instance.
            'svg_fragment_filename': Generated filename relative to MEDIA_ROOT.
            'dangerous_tag_counts': dict of {tag_name: count} for dangerous tags found.
            'dangerous_attr_counts': dict of {attr_name: count} for dangerous attrs found.

    Raises:
        ValueError: If content is not valid SVG or missing viewBox.
    """
    root = ET.fromstring( svg_content )
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError( 'Content is not a valid SVG.' )

    view_box_str = root.attrib.get( 'viewBox' )
    if not view_box_str:
        raise ValueError( 'SVG must contain a viewBox attribute.' )

    svg_viewbox = SvgViewBox.from_attribute_value( view_box_str )

    dangerous_tag_counts = dict()
    dangerous_attr_counts = dict()

    for element in list( root.iter() ):
        if element is root:
            continue

        if element.tag.startswith( '{http://www.w3.org/2000/svg}' ):
            element.tag = element.tag.split( '}', 1 )[1]

        tag_name = element.tag.split( '}' )[-1]
        if tag_name in DANGEROUS_TAGS:
            dangerous_tag_counts[tag_name] = dangerous_tag_counts.get( tag_name, 0 ) + 1
            if remove_dangerous:
                logger.debug( f'Removing dangerous SVG tag "{tag_name}"' )
                root.remove( element )
            continue

        for attr_name in list( element.attrib ):
            if attr_name in DANGEROUS_ATTRS:
                dangerous_attr_counts[attr_name] = dangerous_attr_counts.get( attr_name, 0 ) + 1
                if remove_dangerous:
                    logger.debug( f'Removing dangerous SVG attribute "{attr_name}"' )
                    del element.attrib[attr_name]
            elif attr_name in HREF_ATTRS:
                attr_value = element.attrib[attr_name].strip()
                if not attr_value.startswith( '#' ):
                    dangerous_attr_counts[attr_name] = dangerous_attr_counts.get( attr_name, 0 ) + 1
                    if remove_dangerous:
                        logger.debug( f'Removing dangerous SVG href "{attr_name}={attr_value}"' )
                        del element.attrib[attr_name]

    inner_content = ''.join(
        ET.tostring( element, encoding='unicode' ) for element in root
    )

    svg_fragment_filename = os.path.join(
        media_destination_directory,
        generate_unique_filename( source_filename ),
    )

    return {
        'svg_fragment_content': inner_content,
        'svg_viewbox': svg_viewbox,
        'svg_fragment_filename': svg_fragment_filename,
        'dangerous_tag_counts': dangerous_tag_counts,
        'dangerous_attr_counts': dangerous_attr_counts,
    }
