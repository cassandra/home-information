import logging
import os

from django import forms
from django.conf import settings

from hi.apps.common.svg_file_form import SvgFileForm

logger = logging.getLogger(__name__)


class LocationAddForm( SvgFileForm ):

    name = forms.CharField(
        label = 'Location Name',
        required = True,
    )

    def get_default_source_directory(self):
        return os.path.join(
            settings.BASE_DIR,
            'static',
            'img',
        )

    def get_default_basename(self):
        return 'location-default.svg'
    
    def get_media_destination_directory(self):
        return 'location/svg'

    
class LocationViewAddForm(forms.Form):

    name = forms.CharField()
