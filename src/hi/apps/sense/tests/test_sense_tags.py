import logging

from django.template import Context, Template

from hi.apps.entity.models import Entity, EntityState
from hi.testing.base_test_case import BaseTestCase

logging.disable( logging.CRITICAL )


class TestRenderStateValueText( BaseTestCase ):
    """``render_state_value_text`` is the EntityStatus-layer dispatch
    that resolves the per-state-type value-text template, with
    fallback to the default. Lives in the sense app rather than on
    ``EntityStateType`` because the path scheme is a frontend
    convention, not a model property — parallel to
    ``include_controller_widget`` for the interactive controller side."""

    def _render( self, entity_state, value ):
        return Template(
            '{% load sense_tags %}'
            '{% render_state_value_text entity_state value %}'
        ).render( Context({ 'entity_state': entity_state, 'value': value }) )

    def test_resolves_per_state_type_template_when_present( self ):
        entity = Entity.objects.create(
            name = 'Thermometer', entity_type_str = 'THERMOMETER',
        )
        state = EntityState.objects.create(
            entity = entity, entity_state_type_str = 'TEMPERATURE', units = '°C',
        )
        # ``value_text_temperature.html`` exists; rendering should
        # produce its content (the as_display_value filter output),
        # not the default template's output. The filter passes through
        # ConsoleConverterHelper which converts to the user's preferred
        # display unit — assert a temperature unit symbol is present,
        # confirming the temperature-specific template ran.
        output = self._render( state, '21' ).strip()
        self.assertTrue( output )
        self.assertIn( '°', output )

    def test_falls_back_to_default_for_unimplemented_state_type( self ):
        # No ``value_text_on_off.html`` exists — must fall through to
        # ``value_text_default.html`` without raising.
        entity = Entity.objects.create(
            name = 'Switch', entity_type_str = 'WALL_SWITCH',
        )
        state = EntityState.objects.create(
            entity = entity, entity_state_type_str = 'ON_OFF',
        )
        output = self._render( state, 'on' ).strip()
        # Default template renders through value_label filter for
        # unit-less values — output is non-empty.
        self.assertTrue( output )
