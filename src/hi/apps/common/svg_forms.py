import logging
import os
import xml.etree.ElementTree as ET

from django import forms
from django.core.exceptions import ValidationError

from hi.apps.common.svg_utils import process_svg_content

logger = logging.getLogger(__name__)


class SvgDecimalFormField( forms.FloatField ):
    """
    Use this for ModelForm that have SvgDecimalField model fields.  Using
    a Decimal field in to form is fraught with issues if submitting
    higher precision than Decimal field allows.
    """
    def __init__( self,
                  *args,
                  min_value  : float  = None,
                  max_value  : float  = None,
                  **kwargs ):
        super().__init__(*args, **kwargs)
        self.min_value = min_value
        self.max_value = max_value
        return
    
    def clean( self, value ):
        value = super().clean( value )
        if value is not None:
            if ( self.min_value is not None ) and ( value < self.min_value ):
                value = self.min_value
            if ( self.max_value is not None ) and ( value > self.max_value ):
                value = self.max_value
        return value
       

class SvgFileForm(forms.Form):
    """
    For uploading SVG files while extracting the viewbox and writing
    without the enclosing <svg> element as needed by various HI app views. Also
    detects and can remove dangerous tags and attributes.
    """
    svg_file = forms.FileField(
        label = 'Select an SVG file',
        required = False,
        widget=forms.ClearableFileInput(
            attrs={
                'class': 'custom-file-input',
                'id': 'svg-file-input',
            }
        )
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

    def allow_default_svg_file(self) -> bool:
        """ If returns 'True', then also need to implement these:

                get_default_source_directory()
                get_default_basename()
        """
        raise NotImplementedError( 'Subclasses must override this method.' )

    def get_default_source_directory(self):
        # e.g., static image area
        return None

    def get_default_basename(self):
        # Base filename for the default source (and destination) files.
        return None

    def get_media_destination_directory(self):
        # Relative to MEDIA_ROOT.
        raise NotImplementedError( 'Subclasses must override this method.' )

    def get_default_svg_content(self):
        default_svg_path = os.path.join(
            self.get_default_source_directory(),
            self.get_default_basename(),
        )
        with open( default_svg_path, 'r' ) as f:
            return f.read()
    
    MAX_SVG_FILE_SIZE_MEGABYTES = 5
    MAX_SVG_FILE_SIZE_BYTES = MAX_SVG_FILE_SIZE_MEGABYTES * 1024 * 1024

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
        else:
            require_svg_file = False
            
        remove_dangerous_svg_items = cleaned_data.get( 'remove_dangerous_svg_items' )

        svg_file_handle = cleaned_data.get('svg_file')
        if not svg_file_handle:
            if not self.allow_default_svg_file():
                raise ValidationError( 'You need to select an SVG file.' )
            if require_svg_file:
                raise ValidationError( 'You need to re-select the SVG file.' )

            svg_content = self.get_default_svg_content()
            svg_filename = self.get_default_basename()
        else:
            svg_file_handle.seek(0)  # Guard against multiple calls to clean()
            svg_content = svg_file_handle.read().decode('utf-8')
            svg_filename = svg_file_handle.name
            
        try:
            if len(svg_content) > self.MAX_SVG_FILE_SIZE_BYTES:
                raise ValidationError( f'SVG file too large. Max {self.MAX_SVG_FILE_SIZE_MEGABYTES} MB.' )

            result = process_svg_content(
                svg_content = svg_content,
                media_destination_directory = self.get_media_destination_directory(),
                source_filename = svg_filename,
                remove_dangerous = bool( remove_dangerous_svg_items ),
            )

            self._dangerous_tag_counts = result['dangerous_tag_counts']
            self._dangerous_attr_counts = result['dangerous_attr_counts']

            if ( not remove_dangerous_svg_items
                 and (( len(self._dangerous_tag_counts) + len(self._dangerous_attr_counts) ) > 0 )):
                self._add_dangerous_messages()
                self.fields['remove_dangerous_svg_items'].widget.attrs.update( { 'style': '' } )
                self.data = self.data.copy()
                self.data['has_dangerous_svg_items'] = 'true'
                self._has_dangerous_svg_items = True

            cleaned_data['svg_fragment_content'] = result['svg_fragment_content']
            cleaned_data['svg_viewbox'] = result['svg_viewbox']
            cleaned_data['svg_fragment_filename'] = result['svg_fragment_filename']

        except ET.ParseError as pe:
            logger.exception( pe )
            raise ValidationError( 'The uploaded file is not a valid XML (SVG) file.' )
        except ValueError as ve:
            raise ValidationError( str(ve) )
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
