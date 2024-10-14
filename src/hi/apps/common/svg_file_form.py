import logging
import os
import time
import xml.etree.ElementTree as ET

from django import forms
from django.core.exceptions import ValidationError

from hi.apps.common.svg_models import SvgViewBox

logger = logging.getLogger(__name__)

# Need this to avoid library adding "ns0:" namespacing when writing content.
ET.register_namespace('', 'http://www.w3.org/2000/svg')


class SvgFileForm(forms.Form):

    svg_file = forms.FileField(
        label = 'SVG file',
        required = False,
    )
    remove_dangerous_svg_items = forms.BooleanField(
        label = 'Remove dangerous SVG items?',
        widget = forms.CheckboxInput(
            attrs = {
                'class': 'form-check-input',
                'style': 'display: none;',  # Conditionally shown only 
            }
        ),
        required = False,
    )
    has_dangerous_svg_items = forms.CharField(
        widget = forms.HiddenInput(),
        initial = 'false',
        required = False,
    )

    def get_default_source_directory(self):
        # e.g., static image area
        raise NotImplementedError( 'Subclasses must override this method.' )

    def get_default_basename(self):
        # Base filename for the default source (and destination) files.
        raise NotImplementedError( 'Subclasses must override this method.' )

    def get_media_destination_directory(self):
        # Relative to MEDIA_ROOT.
        raise NotImplementedError( 'Subclasses must override this method.' )
    
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._has_dangerous_svg_items = bool( self.data.get('has_dangerous_svg_items', 'false' ) == 'true' )
        if self._has_dangerous_svg_items:
            self.fields['remove_dangerous_svg_items'].widget.attrs.update( { 'style': '' } )
        return
        
    def clean(self):
        cleaned_data = super().clean()

        self._dangerous_tag_counts = dict()
        self._dangerous_attr_counts = dict()
        
        self._has_dangerous_svg_items = bool(
            cleaned_data.get( 'has_dangerous_svg_items', 'false' ) == 'true'
        )
        if self._has_dangerous_svg_items:
            require_svg_file = True
            
        remove_dangerous_svg_items = cleaned_data.get( 'remove_dangerous_svg_items' )

        svg_file_handle = cleaned_data.get('svg_file')
        if not svg_file_handle:
            if require_svg_file:
                raise ValidationError( 'You need to re-select the SVG file.' )

            default_svg_path = os.path.join(
                self.get_default_source_directory(),
                self.get_default_basename(),
            )
            with open( default_svg_path, 'r' ) as f:
                svg_content = f.read()
            svg_filename = self.get_default_basename()          
        else:
            svg_file_handle.seek(0)  # Guard against multiple calls to clean()
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
                    self._increment_dangerous_tag_count( tag_name )
                    continue
                
                for attr_name in list(element.attrib):
                    if attr_name in self.DANGEROUS_ATTRS:
                        logger.debug(f'Removing dangerous SVG attribute "{attr_name}"')
                        del element.attrib[attr_name]
                        self._increment_dangerous_attr_count( attr_name )
                    continue

                continue
            
            if ( not remove_dangerous_svg_items
                 and (( len(self._dangerous_tag_counts) + len(self._dangerous_attr_counts) ) > 0 )):
                self._add_dangerous_messages()
                self.fields['remove_dangerous_svg_items'].widget.attrs.update( { 'style': '' } )
                self.data = self.data.copy()  # Need a mutable copy to change this data
                self.data['has_dangerous_svg_items'] = 'true'
                self._has_dangerous_svg_items = True
                
            inner_content = ''.join( ET.tostring( element, encoding = 'unicode' ) for element in root )
            cleaned_data['svg_fragment_content'] = inner_content

            svg_fragment_filename = os.path.join(
                self.get_media_destination_directory(),
                self.generate_unique_filename( svg_filename ),
            )
            cleaned_data['svg_fragment_filename'] = svg_fragment_filename
            
        except ET.ParseError as pe:
            logger.exception( pe )
            raise ValidationError( 'The uploaded file is not a valid XML (SVG) file.' )
        except Exception as e:
            logger.exception( e )
            raise ValidationError(f'Error processing the SVG file: {str(e)}' )

        return cleaned_data

    def show_remove_dangerous_svg_items(self):
        return self._has_dangerous_svg_items

    def _increment_dangerous_tag_count( self, tag_name : str ):
        if tag_name in self._dangerous_tag_counts:
            self._dangerous_tag_counts[tag_name] += 1
        else:
            self._dangerous_tag_counts[tag_name] = 1
        return

    def _increment_dangerous_attr_count( self, attr_name : str ):
        if attr_name in self._dangerous_attr_counts:
            self._dangerous_attr_counts[attr_name] += 1
        else:
            self._dangerous_attr_counts[attr_name] = 1
        return
    
    def _add_dangerous_messages(self):
        self.add_error( 'svg_file', 'Dangerous SVG items found which are not allowed.' )
        self.add_error( 'svg_file', 'Confirm changes to have them removed duringn the upload.' )
        self.add_error( 'svg_file', 'The dangerous items (with counts) are:' )
        for tag_name, count in self._dangerous_tag_counts.items():
            self.add_error( 'svg_file', f'- Tag: <{tag_name}>, Count: {count:,} ' )
            continue
        for attr_name, count in self._dangerous_attr_counts.items():
            self.add_error( 'svg_file', f'- Attr: {attr_name}, Count: {count:,} ' )
            continue
        return
    
    def generate_unique_filename( self, filename : str ):
        original_name, extension = os.path.splitext( filename )
        timestamp = int( time.time() )
        unique_name = f'{original_name}-{timestamp}{extension}'
        return unique_name
