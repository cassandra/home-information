import logging

from django.http import Http404
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.location.svg_item_factory import SvgItemFactory

from hi.constants import DIVID
from hi.decorators import edit_required

from . import forms

logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class EntityPositionEditView( View ):

    def post(self, request, *args, **kwargs):

        entity_id = kwargs.get('entity_id')
        location = request.view_parameters.location
        try:
            entity_position = EntityPosition.objects.get(
                id = entity_id,
                location = location,
            )
        except Entity.DoesNotExist:
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
