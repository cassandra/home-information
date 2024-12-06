import logging

from django import forms

from hi.apps.alert.enums import AlarmLevel, SecurityPosture
from hi.apps.control.models import Controller
from hi.apps.common.forms import CustomBaseFormSet
from hi.apps.entity.edit.forms import EntityStateSelectModelFormMixin
from hi.apps.entity.models import EntityState
import hi.apps.event.models as models

logger = logging.getLogger(__name__)


class EventDefinitionForm( forms.ModelForm ):

    class Meta:
        model = models.EventDefinition
        fields = (
            'name',
            'event_window_secs',
            'dedupe_window_secs',
            'enabled',
        )

        
class EventClauseForm( forms.ModelForm, EntityStateSelectModelFormMixin ):

    class Meta:
        model = models.EventClause
        fields = (
            'entity_state',
            'value',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        entity_state = self.get_instance( cls = EntityState, field_name = 'entity_state' )
        self.set_dynamic_entity_state_values_choices(
            select_field_name = 'entity_state',
            value_field_name = 'value',
            entity_state = entity_state,
        )
        return
    
        
class AlarmActionForm( forms.ModelForm ):

    class Meta:
        model = models.AlarmAction
        fields = (
            'security_posture_str',
            'alarm_level_str',
            'alarm_lifetime_secs',
        )

    security_posture_str = forms.ChoiceField(
        label = 'Security Posture',
        choices = SecurityPosture.choices,
        initial = SecurityPosture.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )
    alarm_level_str = forms.ChoiceField(
        label = 'Alarm Level',
        choices = AlarmLevel.choices,
        initial = AlarmLevel.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )

    
class ControlActionForm( forms.ModelForm, EntityStateSelectModelFormMixin ):

    class Meta:
        model = models.ControlAction
        fields = (
            'controller',
            'value',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        controller = self.get_instance( cls = Controller, field_name = 'controller' )
        if controller:
            entity_state = controller.entity_state
        else:
            entity_state = None
        self.set_dynamic_entity_state_values_choices(
            select_field_name = 'controller',
            value_field_name = 'value',
            entity_state = entity_state,
        )
        return

        
EventClauseFormSet = forms.inlineformset_factory(
    models.EventDefinition,
    models.EventClause,
    form = EventClauseForm,
    extra = 1,
    max_num = 100,
    absolute_max = 100,
    can_delete = True,
    formset = CustomBaseFormSet,
)

        
AlarmActionFormSet = forms.inlineformset_factory(
    models.EventDefinition,
    models.AlarmAction,
    form = AlarmActionForm,
    extra = 1,
    max_num = 100,
    absolute_max = 100,
    can_delete = True,
    formset = CustomBaseFormSet,
)

        
ControlActionFormSet = forms.inlineformset_factory(
    models.EventDefinition,
    models.ControlAction,
    form = ControlActionForm,
    extra = 1,
    max_num = 100,
    absolute_max = 100,
    can_delete = True,
    formset = CustomBaseFormSet,
)
