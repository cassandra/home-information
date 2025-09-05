from dataclasses import dataclass

from django.db.models import Model
from django.forms import ModelForm, BaseInlineFormSet
from django.db.models import QuerySet

from .edit_context import AttributeItemEditContext
from .models import AttributeModel


@dataclass
class AttributeEditFormData:
    owner_form                 : ModelForm
    file_attributes            : QuerySet[AttributeModel]
    regular_attributes_formset : BaseInlineFormSet
    error_count                : int               = 0


@dataclass
class AttributeMultiEditFormData:
    attr_item_context  : AttributeItemEditContext
    edit_form_data     : AttributeEditFormData

    @property
    def owner(self) -> Model:
        return self.attr_item_context.owner
    
    @property
    def owner_form(self) -> ModelForm:
        return self.edit_form_data.owner_form
    
    @property
    def file_attributes(self) -> QuerySet[AttributeModel]:
        return self.edit_form_data.file_attributes
    
    @property
    def context(self):
        return self.attr_item_context

    @property
    def regular_attributes_formset(self):
        return self.edit_form_data.regular_attributes_formset

    @property
    def formset(self):
        return self.edit_form_data.regular_attributes_formset

    @property
    def error_count(self):
        return self.edit_form_data.error_count
    
