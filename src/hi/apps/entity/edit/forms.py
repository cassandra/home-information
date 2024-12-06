import logging
from typing import Type

from django import forms

from hi.apps.entity.enums import EntityStateValue
from hi.apps.entity.models import EntityPosition, EntityState
from hi.apps.location.edit.forms import LocationItemPositionForm

logger = logging.getLogger(__name__)


class EntityPositionForm( LocationItemPositionForm ):
    class Meta( LocationItemPositionForm.Meta ):
        model = EntityPosition


class EntityStateSelectModelFormMixin:

    def get_instance( self, cls : Type, field_name : str ):
        id_field_name = f'{field_name}_id'
        
        instance_or_id = None
        if field_name in self.initial:
            instance_or_id = self.initial.get( field_name )
        elif hasattr( self.instance, field_name ):
            instance_or_id = getattr( self.instance, field_name )
        elif hasattr( self.instance, id_field_name ):
            instance_or_id = getattr( self.instance, id_field_name )

        instance = None
        if instance_or_id:
            if isinstance( instance_or_id, int ):
                try:
                    instance = cls.objects.get( id = instance_or_id )
                except cls.DoesNotExist:
                    logger.warning(f'No id={instance_or_id} for {cls.__name__} in {self.__class__.__name__}')
            else:
                instance = instance_or_id
        return instance

    def set_dynamic_entity_state_values_choices( self,
                                                 select_field_name  : str,
                                                 value_field_name   : str,
                                                 entity_state       : EntityState ):
        self.fields[value_field_name].widget = forms.TextInput()
        if entity_state:
            choices_list = entity_state.choices()
            if choices_list:
                self.fields[value_field_name].widget = forms.Select( choices = choices_list )

        value_field_id = f'id_{self.prefix}-{value_field_name}'
        js_onchange = f'Hi.setEntityStateValueSelect("{value_field_id}", "{select_field_name}", this.value);'
        self.fields[select_field_name].widget.attrs['onchange'] = js_onchange
   
        return
