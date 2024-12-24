from dataclasses import fields, MISSING
from datetime import datetime
from typing import Type

from django import forms

from .transient_models import SimEntity
from .models import SimProfile


class SimProfileForm( forms.ModelForm ):
    
    class Meta:
        model = SimProfile
        fields = (
            'name',
        )


class SimEntityForm( forms.Form ):
    """
    Dynamically build a Django form from a subclass of SimEntity.
    """

    DATACLASS_TO_FORM_FIELD = {
        str: forms.CharField,
        int: forms.IntegerField,
        float: forms.FloatField,
        datetime: forms.DateTimeField,
        bool: forms.BooleanField,
    }
    
    def __init__(self, sim_entity_class: Type[ SimEntity ], *args, initial = None, **kwargs):
        super().__init__(*args, **kwargs)

        self._sim_entity_class = sim_entity_class
        
        for field in fields( sim_entity_class ):
            field_type = field.type
            form_field_class = self.DATACLASS_TO_FORM_FIELD.get( field_type, None )
            if not form_field_class:
                raise ValueError( f'Unsupported field type: {field_type}' )
            
            default_value = None if field.default is MISSING else field.default
            field_initial = initial.get( field.name, default_value ) if initial else default_value

            self.fields[field.name] = form_field_class(
                initial = field_initial,
                required = field.default is MISSING,
                label = field.name.replace("_", " ").capitalize(),
            )
            continue
        return

    @property
    def sim_entity_name(self):
        return self._sim_entity_class.__name__
