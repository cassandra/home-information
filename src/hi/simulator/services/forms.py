from dataclasses import fields, MISSING
from datetime import datetime
from typing import Type

from django import forms

from .base_models import SimEntityFields


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

        # Fields rendered as multi-checkbox pickers (csv_choices metadata).
        self._csv_choice_field_names = set()

        # Fields whose dataclass type is ``list``. clean() coerces these
        # back to a list regardless of widget (checkbox or text input), so
        # the dataclass keeps its list shape. A ``str`` field with
        # csv_choices is NOT in this set and stays a CSV string (HomeBox).
        self._list_field_names = set()

        for field in fields( sim_entity_fields_class ):
            metadata = field.metadata or {}
            help_text = metadata.get( 'help_text', '' )
            csv_choices = metadata.get( 'csv_choices' )

            if field.type is list:
                self._list_field_names.add( field.name )

            if csv_choices is not None:
                self._add_csv_choice_field(
                    field = field,
                    choices_source = csv_choices,
                    help_text = help_text,
                    initial = initial,
                )
                continue

            if field.type is list:
                self._add_list_field(
                    field = field,
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
        """Render a dataclass field as a multi-checkbox picker. The
        widget converts initial CSV-or-list → list at render time; at
        submit time ``clean()`` coerces the selection back to the
        dataclass's shape — a list for a ``list`` field, or a CSV string
        for a ``str`` field (e.g. HomeBox ``attachment_keys``)."""
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

    def _add_list_field(self, field, help_text, initial):
        """Fallback for a plain ``list`` field that has no ``csv_choices``:
        a comma-separated text input. ``clean()`` splits it back to a list
        so the dataclass keeps its ``list`` shape. (List fields are tracked
        as list-typed in ``__init__``, not here.)"""
        if field.default_factory is not MISSING:
            default_value = field.default_factory()
        elif field.default is not MISSING:
            default_value = field.default
        else:
            default_value = []
        raw_initial = initial.get( field.name, default_value ) if initial else default_value
        if isinstance( raw_initial, (list, tuple) ):
            field_initial = ', '.join( str( item ) for item in raw_initial )
        else:
            field_initial = raw_initial or ''

        self.fields[field.name] = forms.CharField(
            initial = field_initial,
            required = False,
            label = field.name.replace("_", " ").capitalize(),
            help_text = help_text or 'Comma-separated list.',
        )
        return

    def clean(self):
        cleaned = super().clean()
        # Coerce multi-value fields to the shape the dataclass expects.
        # A ``list``-typed field becomes a list; a ``str``-typed
        # csv_choices field (e.g. HomeBox attachment_keys) becomes a CSV
        # string. The widget (checkbox vs text) is independent of the
        # target shape. Must be idempotent: the view calls clean() again
        # after is_valid() has already run it once, so each branch leaves
        # an already-coerced value unchanged.
        for name in ( self._csv_choice_field_names | self._list_field_names ):
            value = cleaned.get( name )
            if name in self._list_field_names:
                # Target shape: list. From the text widget it is a CSV
                # string; from the checkbox widget it is already a list.
                if isinstance( value, str ):
                    cleaned[name] = [
                        token.strip() for token in value.split(',') if token.strip()
                    ]
                elif isinstance( value, (list, tuple) ):
                    cleaned[name] = list( value )
            elif isinstance( value, (list, tuple) ):
                # str-typed csv_choices field: join the selection to CSV
                # (already a string on a second pass -> left untouched).
                cleaned[name] = ','.join( value )
        return cleaned
