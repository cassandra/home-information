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


class TestStateValueStatus( BaseTestCase ):
    """``state_value_status`` routes a single (history) value through the
    same ``EntityStateDisplayData`` dispatch the live display uses, so a
    bucketed numeric type colors the same way it does on the SVG icon /
    status panels instead of emitting the raw value as the status token."""

    def _render( self, entity_state, value ):
        return Template(
            '{% load sense_tags %}'
            '{% state_value_status entity_state value %}'
        ).render( Context({ 'entity_state': entity_state, 'value': value }) ).strip()

    def test_bucketed_type_emits_dispatched_token_not_raw_value( self ):
        # A TEMPERATURE reading's raw value ("72") is not its CSS token;
        # the dispatch buckets it to the absolute-temperature band.
        entity = Entity.objects.create(
            name = 'Thermometer', entity_type_str = 'THERMOMETER',
        )
        state = EntityState.objects.create(
            entity = entity, entity_state_type_str = 'TEMPERATURE', units = '°F',
        )
        self.assertEqual( self._render( state, '72' ), 'temperature_pleasant' )

    def test_enum_type_token_matches_raw_value( self ):
        entity = Entity.objects.create(
            name = 'Switch', entity_type_str = 'WALL_SWITCH',
        )
        state = EntityState.objects.create(
            entity = entity, entity_state_type_str = 'ON_OFF',
        )
        self.assertEqual( self._render( state, 'on' ), 'on' )

    def test_unrecognized_value_falls_back_to_raw_value( self ):
        # ON_OFF with an invalid value dispatches to no style; the tag
        # falls back to the raw value so a status attribute is always
        # renderable.
        entity = Entity.objects.create(
            name = 'Switch', entity_type_str = 'WALL_SWITCH',
        )
        state = EntityState.objects.create(
            entity = entity, entity_state_type_str = 'ON_OFF',
        )
        self.assertEqual( self._render( state, 'bogus' ), 'bogus' )
