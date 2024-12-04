import logging

from django.db import transaction
from django.views.generic import View

from hi.apps.location.location_manager import LocationManager
from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.apps.sense.sensor_history_manager import SensorHistoryManager

from hi.hi_async_view import HiModalView, HiSideView

from .entity_manager import EntityManager
from . import forms
from .models import EntityAttribute
from .transient_models import EntityEditData
from .view_mixin import EntityViewMixin

logger = logging.getLogger(__name__)


class EntityEditView( View, EntityViewMixin ):

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )
        entity_edit_data = EntityEditData( entity = entity )
        return self.entity_edit_response(
            request = request,
            entity_edit_data = entity_edit_data,
        )
    
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

    
class EntityStatusView( HiModalView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/modals/entity_status.html'

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        entity_status_data = StatusDisplayManager().get_entity_status_data( entity = entity )
        if not entity_status_data.entity_state_status_data_list:
            return EntityEditView().get( request, *args, **kwargs )
        
        context = entity_status_data.to_template_context()
        return self.modal_response( request, context )

    
class EntityStateHistoryView( HiModalView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/modals/entity_state_history.html'

    def get( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        entity_state_history_data = SensorHistoryManager().get_entity_state_history_data(
            entity = entity,
            is_editing = request.is_editing,
        )
        context = entity_state_history_data.to_template_context()
        return self.modal_response( request, context )


class EntityDetailsView( HiSideView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/edit/panes/entity_details.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        current_location_view = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = LocationManager().get_default_location_view( request = request )

        entity_details_data = EntityManager().get_entity_details_data(
            entity = entity,
            location_view = current_location_view,
            is_editing = request.is_editing,
        )
        return entity_details_data.to_template_context()


    
    
    
