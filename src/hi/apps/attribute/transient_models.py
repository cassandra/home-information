from dataclasses import dataclass

from django.forms import ModelForm, BaseInlineFormSet
from django.db.models import QuerySet

from .edit_context import AttributeItemEditContext
from .models import AttributeModel


@dataclass
class AttributeEditFormData:
    owner_form                 : ModelForm
    file_attributes            : QuerySet[AttributeModel]
    regular_attributes_formset : BaseInlineFormSet


@dataclass
class AttributeMultiEditFormData:
    attr_item_context  : AttributeItemEditContext
    edit_form_data     : AttributeEditFormData
