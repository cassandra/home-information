import logging
import os
import time
import xml.etree.ElementTree as ET

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from hi.apps.common.svg_models import SvgViewBox

logger = logging.getLogger(__name__)

# Need this to avoid library adding "ns0:" namespacing when writing content.
ET.register_namespace('', 'http://www.w3.org/2000/svg')


class LocationForm(forms.Form):

    LOCATION_DEFAULT_FILENAME = 'location-default.svg'
    MEDIA_DIRECTORY = 'location/svg'
    MAX_SVG_FILE_SIZE_MEGABYTES = 5
    MAX_SVG_FILE_SIZE_BYTES = MAX_SVG_FILE_SIZE_MEGABYTES * 1024 * 1024

    DANGEROUS_TAGS = {
        'script', 'foreignObject', 'iframe', 'object',
        'animation', 'audio', 'video', 'style',
    }
    DANGEROUS_ATTRS = {
        'onload', 'onclick', 'onmouseover', 'xlink:href',
        'href',
    }

    name = forms.CharField()

    svg_file = forms.FileField(
        label = 'SVG file',
        required = False,
    )

    def clean(self):
        cleaned_data = super().clean()

        svg_file_handle = cleaned_data.get('svg_file')
        if not svg_file_handle:
            default_svg_path = os.path.join(
                settings.BASE_DIR,
                'static',
                'img',
                self.LOCATION_DEFAULT_FILENAME,
            )
            with open(default_svg_path, 'r') as f:
                svg_content = f.read()
            svg_filename = self.LOCATION_DEFAULT_FILENAME          
        else:
            svg_content = svg_file_handle.read().decode('utf-8')
            svg_filename = svg_file_handle.name
            
        try:
            if len(svg_content) > self.MAX_SVG_FILE_SIZE_BYTES:
                raise ValidationError( f'SVG file too large. Max {self.MAX_SVG_FILE_SIZE_MEGABYTES} MB.' )

            root = ET.fromstring( svg_content )
            if root.tag != '{http://www.w3.org/2000/svg}svg':
                raise ValidationError( 'The uploaded file is not a valid SVG file.' )

            view_box_str = root.attrib.get( 'viewBox' )
            if not view_box_str:
                raise ValidationError( 'The SVG must contain a viewBox attribute.' )

            svg_viewbox = SvgViewBox.from_attribute_value( view_box_str )
            cleaned_data['svg_viewbox'] = svg_viewbox

            # Remove the outer <svg> tag if necessary
            for element in list( root.iter() ):
                if element is root:
                    continue
            
                # Remove the namespace from the child elements
                if element.tag.startswith('{http://www.w3.org/2000/svg}'):
                    element.tag = element.tag.split('}', 1)[1]  # Strip the namespace

                tag_name = element.tag.split('}')[-1]  # Handle namespaces
                if tag_name in self.DANGEROUS_TAGS:
                    logger.debug( f'Removing dangerous SVG tag "{tag_name}"' )
                    root.remove(element)
                    continue
                
                for attr in list(element.attrib):
                    if attr in self.DANGEROUS_ATTRS:
                        logger.debug(f'Removing dangerous SVG attribute "{attr}"')
                        del element.attrib[attr]
                    continue

                continue
            
            inner_content = ''.join( ET.tostring( element, encoding = 'unicode' ) for element in root )
            cleaned_data['svg_fragment_content'] = inner_content

            svg_fragment_filename = os.path.join(
                self.MEDIA_DIRECTORY,
                self.generate_unique_filename( svg_filename ),
            )
            cleaned_data['svg_fragment_filename'] = svg_fragment_filename
            
        except ET.ParseError:
            raise ValidationError( 'The uploaded file is not a valid XML (SVG) file.' )
        except Exception as e:
            raise ValidationError(f'Error processing the SVG file: {str(e)}' )

        return cleaned_data
    
    def generate_unique_filename( self, filename : str ):
        original_name, extension = os.path.splitext( filename )
        timestamp = int( time.time() )
        unique_name = f'{original_name}-{timestamp}{extension}'
        return unique_name

    
class LocationViewForm(forms.Form):

    name = forms.CharField()
