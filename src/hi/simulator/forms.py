from dataclasses import fields, MISSING
from datetime import datetime
from typing import Type

from django import forms

from .base_models import SimEntityFields
from .models import SimProfile


class SimProfileForm( forms.ModelForm ):

    class Meta:
        model = SimProfile
        fields = (
            'name',
        )


class SimEntityFieldsForm( forms.Form ):
    """
    Dynamically build a Django form from a subclass of SimEntityFields.

    Per-field metadata is read from the dataclass's
    ``field.metadata`` mapping:

      * ``csv_choices`` — callable or iterable of ``(value, label)``
        tuples. Switches the form field from a plain ``CharField`` to
        a ``MultipleChoiceField`` rendered as checkboxes; the form
        round-trips between the dataclass's CSV string and the
        widget's list of values, so the underlying dataclass
        ``str`` field shape is preserved.

      * ``help_text`` — string passed straight to the Django form
        field (rendered by the standard form template).
    """

    DATA_TYPE_TO_FORM_FIELD = {
        str: forms.CharField,
        int: forms.IntegerField,
        float: forms.FloatField,
        datetime: forms.DateTimeField,
        bool: forms.BooleanField,
    }

    def __init__(self, sim_entity_fields_class: Type[ SimEntityFields ], *args, initial = None, **kwargs):
        super().__init__(*args, **kwargs)

        # Track which fields use the CSV-choices round-trip so
        # ``clean()`` can rejoin the multi-select list back into a
        # CSV string for the dataclass consumer.
        self._csv_choice_field_names = set()

        for field in fields( sim_entity_fields_class ):
            metadata = field.metadata or {}
            help_text = metadata.get( 'help_text', '' )
            csv_choices = metadata.get( 'csv_choices' )

            if csv_choices is not None:
                self._add_csv_choice_field(
                    field = field,
                    choices_source = csv_choices,
                    help_text = help_text,
                    initial = initial,
                )
                continue

            field_type = field.type
            form_field_class = self.DATA_TYPE_TO_FORM_FIELD.get( field_type, None )
            if not form_field_class:
                raise ValueError( f'Unsupported field type: {field_type}' )

            default_value = None if field.default is MISSING else field.default
            field_initial = initial.get( field.name, default_value ) if initial else default_value

            self.fields[field.name] = form_field_class(
                initial = field_initial,
                required = field.default is MISSING,
                label = field.name.replace("_", " ").capitalize(),
                help_text = help_text,
            )
            continue
        return

    def _add_csv_choice_field(self, field, choices_source, help_text, initial):
        """Render a CSV-string dataclass field as a multi-checkbox
        picker. The dataclass keeps its plain ``str`` shape; the
        form converts initial CSV → list at render time and
        ``clean()`` converts list → CSV at submit time."""
        choices = choices_source() if callable( choices_source ) else list( choices_source )

        default_value = '' if field.default is MISSING else ( field.default or '' )
        raw_initial = initial.get( field.name, default_value ) if initial else default_value
        if isinstance( raw_initial, str ):
            field_initial = [
                token.strip() for token in raw_initial.split(',') if token.strip()
            ]
        elif isinstance( raw_initial, (list, tuple) ):
            field_initial = list( raw_initial )
        else:
            field_initial = []

        self.fields[field.name] = forms.MultipleChoiceField(
            choices = choices,
            initial = field_initial,
            required = False,
            label = field.name.replace("_", " ").capitalize(),
            widget = forms.CheckboxSelectMultiple,
            help_text = help_text,
        )
        self._csv_choice_field_names.add( field.name )
        return

    def clean(self):
        cleaned = super().clean()
        # Rejoin multi-select lists back into CSV so consumers
        # (the dataclass build path) see the same shape regardless
        # of widget choice.
        for name in self._csv_choice_field_names:
            value = cleaned.get( name )
            if isinstance( value, (list, tuple) ):
                cleaned[name] = ','.join( value )
        return cleaned
