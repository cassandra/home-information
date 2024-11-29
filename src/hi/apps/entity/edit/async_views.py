import logging

from django.db import transaction
from django.http import Http404
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.entity.models import EntityAttribute, EntityPosition
from hi.apps.entity.transient_models import EntityEditData
from hi.apps.entity.view_mixin import EntityViewMixin
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.apps.location.location_manager import LocationManager

from hi.constants import DIVID
from hi.decorators import edit_required

from . import forms

logger = logging.getLogger(__name__)


class EntityEditView( View, EntityViewMixin ):

    def post( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        entity_form = forms.EntityForm( request.POST, instance = entity )
        entity_attribute_formset = forms.EntityAttributeFormSet(
            request.POST,
            request.FILES,
            instance = entity,
            prefix = f'entity-{entity.id}',
        )
        if entity_form.is_valid() and entity_attribute_formset.is_valid():
            with transaction.atomic():
                entity_form.save()   
                entity_attribute_formset.save()
                
            # Recreate to preserve "max" to show new form
            entity_attribute_formset = forms.EntityAttributeFormSet(
                instance = entity,
                prefix = f'entity-{entity.id}',
            )
            status_code = 200
        else:
            status_code = 400
            
        entity_edit_data = EntityEditData(
            entity = entity,
            entity_form = entity_form,
            entity_attribute_formset = entity_attribute_formset,
        )
        return self.entity_edit_response(
            request = request,
            entity_edit_data = entity_edit_data,
            status_code = status_code,
        )

        
class EntityAttributeUploadView( View, EntityViewMixin ):

    def post( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        entity_attribute = EntityAttribute( entity = entity )
        entity_attribute_upload_form = forms.EntityAttributeUploadForm(
            request.POST,
            request.FILES,
            instance = entity_attribute,
        )

        if entity_attribute_upload_form.is_valid():
            with transaction.atomic():
                entity_attribute_upload_form.save()   
            status_code = 200
        else:
            status_code = 400

        entity_edit_data = EntityEditData(
            entity = entity,
            entity_attribute_upload_form = entity_attribute_upload_form,
        )            
        return self.entity_edit_response(
            request = request,
            entity_edit_data = entity_edit_data,
            status_code = status_code,
        )
    
    
@method_decorator( edit_required, name='dispatch' )
class EntityPositionEditView( View, EntityViewMixin ):

    def post(self, request, *args, **kwargs):
        entity = self.get_entity( request, *args, **kwargs )
        location = LocationManager().get_default_location( request = request )
        try:
            entity_position = EntityPosition.objects.get(
                entity = entity,
                location = location,
            )
        except EntityPosition.DoesNotExist:
            raise Http404( request )
        
        entity_position_form = forms.EntityPositionForm(
            request.POST,
            instance = entity_position,
        )
        if entity_position_form.is_valid():
            entity_position_form.save()
        else:
            logger.warning( 'EntityPosition form is invalid.' )
            
        context = {
            'entity': entity_position.entity,
            'entity_position_form': entity_position_form,
        }
        template = get_template( 'entity/edit/panes/entity_position_edit.html' )
        content = template.render( context, request = request )
        insert_map = {
            DIVID['ENTITY_POSITION_EDIT_PANE']: content,
        }

        svg_icon_item = SvgItemFactory().create_svg_icon_item(
            item = entity_position.entity,
            position = entity_position,
            css_class = '',
        )
        set_attributes_map = {
            svg_icon_item.html_id: {
                'transform': svg_icon_item.transform_str,
            }
        }
        return antinode.response(
            insert_map = insert_map,
            set_attributes_map = set_attributes_map,
        )
