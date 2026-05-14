import logging
from unittest.mock import patch

from django.template.exceptions import TemplateDoesNotExist

from hi.apps.entity.enums import EntityType
from hi.apps.entity.state_panel_dispatch import (
    FRAMEWORK_FALLBACK_TEMPLATES,
    SUPPORTED_DISPLAY_CONTEXTS,
    resolve_panel_template,
)
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestResolvePanelTemplate(BaseTestCase):
    """``resolve_panel_template`` walks a three-step chain: the panel's
    context-specific template, the panel's required default (modal.html),
    then the framework's per-context fallback. The framework fallbacks
    are guaranteed to exist; the panel templates may or may not."""

    def test_falls_back_to_framework_default_when_no_panel_exists(self):
        # SMOKE_DETECTOR has no panel templates in Phase 1; resolution
        # lands on the framework fallback for the modal context.
        template_obj = resolve_panel_template(
            entity_type = EntityType.SMOKE_DETECTOR,
            display_context_name = 'modal',
        )
        self.assertEqual(
            template_obj.origin.template_name,
            FRAMEWORK_FALLBACK_TEMPLATES[ 'modal' ],
        )

    def test_falls_back_to_framework_default_for_list_context(self):
        template_obj = resolve_panel_template(
            entity_type = EntityType.SMOKE_DETECTOR,
            display_context_name = 'list',
        )
        self.assertEqual(
            template_obj.origin.template_name,
            FRAMEWORK_FALLBACK_TEMPLATES[ 'list' ],
        )

    def test_falls_back_to_framework_default_for_grid_context(self):
        template_obj = resolve_panel_template(
            entity_type = EntityType.SMOKE_DETECTOR,
            display_context_name = 'grid',
        )
        self.assertEqual(
            template_obj.origin.template_name,
            FRAMEWORK_FALLBACK_TEMPLATES[ 'grid' ],
        )

    def test_returns_panel_context_template_when_present(self):
        # Simulate a panel directory existing for camera with all
        # three context-specific templates.
        with patch(
            'hi.apps.entity.state_panel_dispatch.get_template'
        ) as mock_get_template:
            mock_get_template.side_effect = self._template_existence_simulator({
                'entity/state_panels/camera/grid.html': True,
            })
            template_obj = resolve_panel_template(
                entity_type = EntityType.CAMERA,
                display_context_name = 'grid',
            )
        self.assertEqual(
            mock_get_template.call_args_list[ 0 ].args[ 0 ],
            'entity/state_panels/camera/grid.html',
        )
        self.assertIsNotNone( template_obj )

    def test_list_context_falls_back_to_panel_modal_when_list_absent(self):
        # Panel provides modal.html but not list.html; resolution
        # should reach modal.html, not the framework fallback.
        with patch(
            'hi.apps.entity.state_panel_dispatch.get_template'
        ) as mock_get_template:
            mock_get_template.side_effect = self._template_existence_simulator({
                'entity/state_panels/camera/modal.html': True,
            })
            resolve_panel_template(
                entity_type = EntityType.CAMERA,
                display_context_name = 'list',
            )
            requested_paths = [ call.args[ 0 ] for call in mock_get_template.call_args_list ]
        self.assertIn( 'entity/state_panels/camera/list.html', requested_paths )
        self.assertIn( 'entity/state_panels/camera/modal.html', requested_paths )
        # Resolution stops at modal.html; framework fallback is never asked.
        self.assertNotIn(
            FRAMEWORK_FALLBACK_TEMPLATES[ 'list' ],
            requested_paths,
        )

    def test_modal_context_lookup_order(self):
        # Modal context tries the panel's modal.html, then the framework
        # fallback. There is no intermediate step.
        with patch(
            'hi.apps.entity.state_panel_dispatch.get_template'
        ) as mock_get_template:
            mock_get_template.side_effect = self._template_existence_simulator( {} )
            resolve_panel_template(
                entity_type = EntityType.THERMOSTAT,
                display_context_name = 'modal',
            )
            requested_paths = [ call.args[ 0 ] for call in mock_get_template.call_args_list ]
        # First lookup is panel/modal; last is framework fallback. The
        # middle step (panel/modal again) is harmless duplication.
        self.assertEqual(
            requested_paths[ 0 ],
            'entity/state_panels/thermostat/modal.html',
        )
        self.assertEqual(
            requested_paths[ -1 ],
            FRAMEWORK_FALLBACK_TEMPLATES[ 'modal' ],
        )

    def test_unsupported_context_raises(self):
        with self.assertRaises( ValueError ):
            resolve_panel_template(
                entity_type = EntityType.SMOKE_DETECTOR,
                display_context_name = 'sidebar',
            )

    def test_all_supported_contexts_resolve_to_real_framework_fallbacks(self):
        # Sanity check: every supported context has a framework
        # fallback template that actually exists.
        for context_name in SUPPORTED_DISPLAY_CONTEXTS:
            template_obj = resolve_panel_template(
                entity_type = EntityType.SMOKE_DETECTOR,
                display_context_name = context_name,
            )
            self.assertEqual(
                template_obj.origin.template_name,
                FRAMEWORK_FALLBACK_TEMPLATES[ context_name ],
            )

    # ------------------------------------------------------------------

    def _template_existence_simulator( self, existing_template_names_dict ):
        """Return a mock side_effect that simulates ``get_template``
        finding the listed templates, plus the framework fallbacks
        (which are guaranteed to exist in production)."""
        from django.template.loader import get_template as real_get_template

        existing = set( existing_template_names_dict )
        existing.update( FRAMEWORK_FALLBACK_TEMPLATES.values() )

        def side_effect( template_name ):
            if template_name in existing:
                return real_get_template( FRAMEWORK_FALLBACK_TEMPLATES[ 'modal' ] )
            raise TemplateDoesNotExist( template_name )

        return side_effect
