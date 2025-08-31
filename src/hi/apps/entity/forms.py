from django import forms

from hi.apps.attribute.forms import AttributeForm, AttributeUploadForm
from hi.apps.attribute.enums import AttributeValueType
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity, EntityAttribute


class EntityForm( forms.ModelForm ):

    class Meta:
        model = Entity
        fields = (
            'name',
            'entity_type_str',
        )
        
    entity_type_str = forms.ChoiceField(
        label = 'Type',
        choices = EntityType.choices,
        initial = EntityType.default_value(),
        required = True,
        widget = forms.Select( attrs = { 'class' : 'custom-select' } ),
    )

    
class EntityAttributeForm( AttributeForm ):
    class Meta( AttributeForm.Meta ):
        model = EntityAttribute

        
EntityAttributeFormSet = forms.inlineformset_factory(
    Entity,
    EntityAttribute,
    form = EntityAttributeForm,
    extra = 1,
    max_num = 100,
    absolute_max = 100,
    can_delete = True,
)


class RegularAttributeBaseFormSet(forms.BaseInlineFormSet):
    """Base formset that automatically excludes FILE attributes for regular attribute editing"""
    
    def get_queryset(self):
        """Override to automatically filter out FILE attributes"""
        queryset = super().get_queryset()
        return queryset.exclude(value_type_str=str(AttributeValueType.FILE))


EntityAttributeRegularFormSet = forms.inlineformset_factory(
    Entity,
    EntityAttribute,
    form = EntityAttributeForm,
    formset = RegularAttributeBaseFormSet,
    extra = 1,
    max_num = 100,
    absolute_max = 100,
    can_delete = True,
)


class EntityAttributeUploadForm( AttributeUploadForm ):
    class Meta( AttributeUploadForm.Meta ):
        model = EntityAttribute
