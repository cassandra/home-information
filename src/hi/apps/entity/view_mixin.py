from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest
from django.template.loader import get_template

import hi.apps.common.antinode as antinode
import hi.apps.entity.edit.forms as forms

from hi.apps.entity.models import Entity

from hi.constants import DIVID


class EntityViewMixin:

    def get_entity( self, request, *args, **kwargs ) -> Entity:
        """ Assumes there is a required entity_id in kwargs """
        try:
            entity_id = int( kwargs.get( 'entity_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid entity id.' )
        try:
            return Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404( request )

    def entity_edit_response( self,
                              request                       : HttpRequest,
                              entity                        : Entity,
                              entity_form                   : forms.EntityAttributeFormSet     = None,
                              entity_attribute_formset      : forms.EntityAttributeFormSet     = None,
                              entity_attribute_upload_form  : forms.EntityAttributeUploadForm  = None,
                              status_code                   : int                              = 200 ):

        if not entity_form:
            entity_form = forms.EntityForm(
                instance = entity,
            )
        if not entity_attribute_formset:
            entity_attribute_formset = forms.EntityAttributeFormSet(
                instance = entity,
                prefix = f'entity-{entity.id}',
                form_kwargs = {
                    'show_as_editable': True,
                },
            )
        if not entity_attribute_upload_form:
            entity_attribute_upload_form = forms.EntityAttributeUploadForm(
                instance = entity,
            )
            
        context = {
            'entity': entity,
            'entity_form': entity_form,
            'entity_attribute_formset': entity_attribute_formset,
            'entity_attribute_upload_form': entity_attribute_upload_form,
        }
        template = get_template( 'entity/edit/panes/entity_edit.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['ENTITY_EDIT_PANE']: content,
            },
            status = status_code,
        )
 
