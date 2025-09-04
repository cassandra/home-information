from dataclasses import dataclass

from django.forms import ModelForm, BaseInlineFormSet
from django.db.models import QuerySet

from .models import AttributeModel


@dataclass
class AttributeEditFormData:
    owner_form                 : ModelForm
    file_attributes            : QuerySet[AttributeModel]
    regular_attributes_formset : BaseInlineFormSet
