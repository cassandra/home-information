from django import forms

from hi.apps.common.forms import CustomBaseFormSet

from . import models


class EventDefinitionForm( forms.ModelForm ):

    class Meta:
        model = models.EventDefinition
        fields = (
            'name',
            'event_window_secs',
            'dedupe_window_secs',
            'enabled',
        )

        
class EventClauseForm( forms.ModelForm ):

    class Meta:
        model = models.EventClause
        fields = (
            'entity_state',
            'value',
        )

        
class AlarmActionForm( forms.ModelForm ):

    class Meta:
        model = models.AlarmAction
        fields = (
            'security_posture_str',
            'alarm_level_str',
            'alarm_lifetime_secs',
        )

        
class ControlActionForm( forms.ModelForm ):

    class Meta:
        model = models.ControlAction
        fields = (
            'controller',
            'value',
        )

        
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
