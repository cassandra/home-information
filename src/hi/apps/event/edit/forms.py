import json
import logging

from django import forms

from hi.apps.alert.enums import AlarmLevel
from hi.apps.control.models import Controller
from hi.apps.common.forms import CustomBaseFormSet
from hi.apps.entity.edit.forms import EntityStateSelectModelFormMixin
from hi.apps.entity.models import EntityState
from hi.apps.event.enums import EventClauseOperator, EventType
import hi.apps.event.models as models
from hi.apps.security.enums import SecurityLevel

logger = logging.getLogger(__name__)


class EventDefinitionForm( forms.ModelForm ):

    class Meta:
        model = models.EventDefinition
        fields = (
            'name',
            'event_type_str',
            'event_window_secs',
            'dedupe_window_secs',
            'enabled',
        )

    event_type_str = forms.ChoiceField(
        label = 'Match Type',
        choices = EventType.choices,
        initial = EventType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ( 'name', 'event_window_secs', 'dedupe_window_secs' ):
            self.fields[field_name].widget.attrs.setdefault( 'class', 'form-control' )
        return

        
class EventClauseForm( forms.ModelForm, EntityStateSelectModelFormMixin ):

    class Meta:
        model = models.EventClause
        fields = (
            'entity_state',
            'value_operator_str',
            'value',
        )

    value_operator_str = forms.ChoiceField(
        label = 'Operator',
        choices = EventClauseOperator.choices,
        initial = EventClauseOperator.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        entity_state = self.get_instance( cls = EntityState, field_name = 'entity_state' )
        self.set_dynamic_entity_state_values_choices(
            select_field_name = 'entity_state',
            value_field_name = 'value',
            entity_state = entity_state,
        )
        self.fields['entity_state'].widget.attrs.update({ 'class': 'custom-select' })
        self.fields['value'].widget.attrs.update({ 'class': 'custom-select' })
        # When the saved operator is IN and the state has discrete
        # choices, render value as SelectMultiple so the persisted
        # selection round-trips on edit-page load.
        operator_str = self[ 'value_operator_str' ].value() or ''
        if ( operator_str == str( EventClauseOperator.IN )
             and entity_state and entity_state.choices() ):
            self.fields['value'].widget = forms.SelectMultiple(
                choices = entity_state.choices(),
            )
            self.fields['value'].widget.attrs['class'] = 'custom-select'
            if self.instance and self.instance.pk:
                self.initial['value'] = sorted(
                    self.instance.in_value_members(),
                )
        value_field_id = f'id_{self.prefix}-value' if self.prefix else 'id_value'
        operator_field_id = f'id_{self.prefix}-value_operator_str' if self.prefix else 'id_value_operator_str'
        self.fields['value_operator_str'].widget.attrs['onchange'] = (
            f'Hi.setEventClauseValueOperatorWidget('
            f'"{operator_field_id}", "{value_field_id}");'
        )
        # Single source of truth for "which operators are numeric":
        # the enum. JS reads this attribute to drive its on-change
        # widget swap rather than hard-coding the list.
        self.fields['value_operator_str'].widget.attrs['data-numeric-ops'] = (
            json.dumps([
                str( op ) for op in EventClauseOperator if op.is_numeric
            ])
        )
        if 'class' not in self.fields['value'].widget.attrs:
            self.fields['value'].widget.attrs['class'] = 'form-control'
        return

    def clean(self):
        cleaned = super().clean()
        op_str = cleaned.get( 'value_operator_str' )
        op = EventClauseOperator.from_name_safe( op_str ) if op_str else None
        # For IN, reassemble the POSTed value(s) into the model's
        # comma-delimited storage shape. ``getlist`` is uniform across
        # SelectMultiple (N entries) and TextInput (1 entry with
        # embedded commas) — the latter round-trips unchanged.
        if op == EventClauseOperator.IN:
            submitted = self.data.getlist( self.add_prefix( 'value' ))
            cleaned['value'] = models.EventClause.serialize_in_members( submitted )
        value = cleaned.get( 'value' )
        # The matcher silently no-ops on parse failure for numeric ops;
        # reject at form time so the user gets immediate feedback
        # instead of a clause that never fires.
        if op and op.is_numeric and value:
            try:
                float( value )
            except ( ValueError, TypeError ):
                self.add_error(
                    'value',
                    f'Numeric value required for operator "{op_str}".',
                )
        return cleaned
    
        
class AlarmActionForm( forms.ModelForm ):

    class Meta:
        model = models.AlarmAction
        fields = (
            'security_level_str',
            'alarm_level_str',
            'alarm_lifetime_secs',
        )

    security_level_str = forms.ChoiceField(
        label = 'Security Level',
        choices = SecurityLevel.non_off_choices,
        initial = SecurityLevel.default_value(),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alarm_lifetime_secs'].widget.attrs.setdefault(
            'class', 'form-control',
        )
        return


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
        self.fields['controller'].widget.attrs.update({ 'class': 'custom-select' })
        if 'class' not in self.fields['value'].widget.attrs:
            self.fields['value'].widget.attrs['class'] = 'form-control'
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
