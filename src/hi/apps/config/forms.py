from django import forms
from django.core.exceptions import ValidationError

from hi.apps.attribute.forms import AttributeForm, RegularAttributeBaseFormSet

from .models import Subsystem, SubsystemAttribute


class SubsystemAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = SubsystemAttribute

    def clean(self):
        cleaned_data = super().clean()
        self._apply_setting_validator( cleaned_data )
        return cleaned_data

    def _apply_setting_validator( self, cleaned_data ):
        # Only validate edits: an unchanged stored value that predates
        # its validator must not block saving the other settings.
        if not self.instance.pk or not self.instance.is_editable:
            return
        if 'value' not in self.changed_data or self.has_error( 'value' ):
            return
        definition = self.instance.setting_definition
        if not definition or not definition.validator:
            return
        try:
            definition.validator( cleaned_data.get( 'value' ) )
        except ValidationError as e:
            self.add_error( 'value', e )
        return

    
SubsystemAttributeRegularFormSet = forms.inlineformset_factory(
    Subsystem,
    SubsystemAttribute,
    form = SubsystemAttributeForm,
    formset = RegularAttributeBaseFormSet,
    extra = 0,
    max_num = 100,
    absolute_max = 100,
    can_delete = False,
)
