import logging

from django.template import Context, Template

from hi.apps.control.models import Controller
from hi.apps.entity.models import Entity, EntityState
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestIncludeControllerWidget(BaseTestCase):
    """``include_controller_widget`` is the EntityStatus-layer dispatch
    that resolves the per-state-type interactive widget template, with
    fallback to the default. Lives in the control app rather than on
    ``EntityStateType`` because the layout assumptions (inline form
    snippet, row-list context) belong to the EntityStatus templates,
    not the model."""

    def _render( self, controller ):
        return Template(
            '{% load control_tags %}'
            '{% include_controller_widget controller %}'
        ).render( Context({ 'controller': controller, 'controller_data': _Dummy(controller) }) )

    def test_resolves_per_state_type_template_when_present(self):
        entity = Entity.objects.create( name = 'Switch', entity_type_str = 'WALL_SWITCH' )
        state = EntityState.objects.create( entity = entity, entity_state_type_str = 'ON_OFF' )
        controller = Controller.objects.create(
            entity_state = state, name = 'sw', controller_type_str = 'DEFAULT',
        )
        # control/panes/controller_on_off.html exists in the codebase; the
        # rendered output should be that template's content (a toggle
        # switch), not the default.
        output = self._render( controller )
        self.assertIn( 'switch-modern', output )

    def test_falls_back_to_default_for_unimplemented_state_type(self):
        # BLOB has no controller_blob.html — must fall through to
        # controller_default.html without raising.
        entity = Entity.objects.create( name = 'Blob', entity_type_str = 'OTHER' )
        state = EntityState.objects.create( entity = entity, entity_state_type_str = 'BLOB' )
        controller = Controller.objects.create(
            entity_state = state, name = 'blob-ctrl', controller_type_str = 'DEFAULT',
        )
        output = self._render( controller )
        # Default template renders without error.
        self.assertIsNotNone( output )


class _Dummy:
    """Minimum surface to render the per-state-type widget templates
    that read ``controller_data.controller`` / ``controller_data.value``."""
    def __init__( self, controller ):
        self.controller = controller
        self.value = ''
        self.css_class = ''
        self.error_list = []
