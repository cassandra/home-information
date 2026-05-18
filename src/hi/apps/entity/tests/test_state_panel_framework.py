import logging

from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatePanel
from hi.apps.entity.state_panel_dispatch import StatePanelDispatcher
from hi.apps.entity.state_panel_registry import EntityStatePanelRegistry
from hi.testing.base_test_case import BaseTestCase


logging.disable( logging.CRITICAL )


def _make_panel( **overrides ) -> EntityStatePanel:
    """Build an EntityStatePanel with sensible defaults for testing.
    Only the attributes the test cares about need to be passed."""
    defaults = dict(
        name             = 'p',
        display_contexts = { DisplayContext.MODAL },
        priority         = 10,
        template_name    = 'entity/state_panels/p/panel.html',
    )
    defaults.update( overrides )
    return EntityStatePanel( **defaults )


class TestEntityStatePanelValidation( BaseTestCase ):

    def test_minimal_construction_succeeds( self ):
        panel = _make_panel()
        self.assertEqual( panel.name, 'p' )
        self.assertIsNone( panel.entity_type )
        self.assertEqual( panel.required_roles, set() )
        self.assertEqual( panel.optional_roles, set() )

    def test_empty_name_rejected( self ):
        with self.assertRaises( TypeError ):
            _make_panel( name = '' )

    def test_non_string_template_name_rejected( self ):
        with self.assertRaises( TypeError ):
            _make_panel( template_name = None )

    def test_empty_display_contexts_rejected( self ):
        with self.assertRaises( TypeError ):
            _make_panel( display_contexts = set() )

    def test_non_context_member_in_display_contexts_rejected( self ):
        with self.assertRaises( TypeError ):
            _make_panel( display_contexts = { 'modal' } )

    def test_non_int_priority_rejected( self ):
        with self.assertRaises( TypeError ):
            _make_panel( priority = '10' )

    def test_non_entity_type_rejected( self ):
        with self.assertRaises( TypeError ):
            _make_panel( entity_type = 'thermostat' )

    def test_overlapping_role_sets_rejected( self ):
        with self.assertRaises( TypeError ):
            _make_panel(
                required_roles = { EntityStateRole.TEMPERATURE },
                optional_roles = { EntityStateRole.TEMPERATURE },
            )

    def test_role_data_template_alias_to_undeclared_role_rejected( self ):
        # Aliasing a role that's not in required_roles | optional_roles
        # is an authoring mistake — the dispatcher would always resolve
        # it to None for typed panels (filtered by-role map) or to
        # whatever happens to be present for fallback panels.
        with self.assertRaises( TypeError ):
            _make_panel(
                required_roles = { EntityStateRole.TEMPERATURE },
                role_data_template_aliases = {
                    'temp_data': EntityStateRole.HUMIDITY,
                },
            )

    def test_role_data_template_alias_must_be_entity_state_role( self ):
        with self.assertRaises( TypeError ):
            _make_panel(
                required_roles = { EntityStateRole.TEMPERATURE },
                role_data_template_aliases = {
                    'temp_data': 'temperature',
                },
            )


class TestEntityStatePanelRegistry( BaseTestCase ):

    def setUp( self ):
        super().setUp()
        self._registry_snapshot = EntityStatePanelRegistry().snapshot_for_tests()
        EntityStatePanelRegistry().restore_for_tests( ( {}, False ) )

    def tearDown( self ):
        EntityStatePanelRegistry().restore_for_tests( self._registry_snapshot )
        super().tearDown()

    def test_register_adds_panel( self ):
        registry = EntityStatePanelRegistry()
        panel = _make_panel( name = 'alpha' )
        registry.register( panel )
        self.assertIs( registry.get_by_name( 'alpha' ), panel )
        self.assertIn( panel, registry.all_panels() )

    def test_re_registering_same_instance_is_idempotent( self ):
        registry = EntityStatePanelRegistry()
        panel = _make_panel( name = 'alpha' )
        registry.register( panel )
        registry.register( panel )
        self.assertEqual( len( registry.all_panels() ), 1 )

    def test_duplicate_name_different_instance_rejected( self ):
        registry = EntityStatePanelRegistry()
        registry.register( _make_panel( name = 'alpha' ) )
        with self.assertRaises( RuntimeError ):
            registry.register( _make_panel( name = 'alpha' ) )


class TestResolvePanel( BaseTestCase ):

    def setUp( self ):
        super().setUp()
        self._registry_snapshot = EntityStatePanelRegistry().snapshot_for_tests()
        EntityStatePanelRegistry().restore_for_tests( ( {}, False ) )

    def tearDown( self ):
        EntityStatePanelRegistry().restore_for_tests( self._registry_snapshot )
        super().tearDown()

    def _register( self, panel ):
        EntityStatePanelRegistry().register( panel )
        return panel

    def test_typed_panel_wins_when_required_roles_present( self ):
        thermostat = self._register( _make_panel(
            name = 'thermostat',
            entity_type = EntityType.THERMOSTAT,
            required_roles = { EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE },
        ) )
        fallback = self._register( _make_panel(
            name = 'fallback', entity_type = None,
        ) )
        resolution = StatePanelDispatcher.resolve_panel(
            entity_type = EntityType.THERMOSTAT,
            display_context = DisplayContext.MODAL,
            present_roles = { EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE },
        )
        self.assertIs( resolution.panel, thermostat )
        self.assertNotIn( fallback, resolution.trace )

    def test_lower_priority_wins_among_typed_matches( self ):
        winner = self._register( _make_panel(
            name = 'specific',
            entity_type = EntityType.THERMOSTAT,
            priority = 10,
            required_roles = { EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE },
        ) )
        self._register( _make_panel(
            name = 'general',
            entity_type = EntityType.THERMOSTAT,
            priority = 20,
        ) )
        resolution = StatePanelDispatcher.resolve_panel(
            entity_type = EntityType.THERMOSTAT,
            display_context = DisplayContext.MODAL,
            present_roles = { EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE },
        )
        self.assertIs( resolution.panel, winner )

    def test_name_breaks_priority_tie_alphabetically( self ):
        a = self._register( _make_panel(
            name = 'aaa', entity_type = EntityType.THERMOSTAT, priority = 10,
        ) )
        self._register( _make_panel(
            name = 'bbb', entity_type = EntityType.THERMOSTAT, priority = 10,
        ) )
        resolution = StatePanelDispatcher.resolve_panel(
            entity_type = EntityType.THERMOSTAT,
            display_context = DisplayContext.MODAL,
            present_roles = set(),
        )
        self.assertIs( resolution.panel, a )

    def test_missing_required_role_disqualifies_typed_panel( self ):
        self._register( _make_panel(
            name = 'thermostat',
            entity_type = EntityType.THERMOSTAT,
            required_roles = { EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE },
        ) )
        fallback = self._register( _make_panel(
            name = 'fallback', entity_type = None,
        ) )
        resolution = StatePanelDispatcher.resolve_panel(
            entity_type = EntityType.THERMOSTAT,
            display_context = DisplayContext.MODAL,
            present_roles = set(),
        )
        self.assertIs( resolution.panel, fallback )

    def test_display_context_mismatch_disqualifies_typed_panel( self ):
        self._register( _make_panel(
            name = 'modal_only',
            entity_type = EntityType.THERMOSTAT,
            display_contexts = { DisplayContext.MODAL },
        ) )
        fallback = self._register( _make_panel(
            name = 'fallback',
            entity_type = None,
            display_contexts = { DisplayContext.MODAL, DisplayContext.GRID },
        ) )
        resolution = StatePanelDispatcher.resolve_panel(
            entity_type = EntityType.THERMOSTAT,
            display_context = DisplayContext.GRID,
            present_roles = set(),
        )
        self.assertIs( resolution.panel, fallback )

    def test_extras_are_roles_outside_declared_set( self ):
        self._register( _make_panel(
            name = 'thermostat',
            entity_type = EntityType.THERMOSTAT,
            required_roles = { EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE },
            optional_roles = { EntityStateRole.HUMIDITY },
        ) )
        resolution = StatePanelDispatcher.resolve_panel(
            entity_type = EntityType.THERMOSTAT,
            display_context = DisplayContext.MODAL,
            present_roles = {
                EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
                EntityStateRole.HUMIDITY,
                EntityStateRole.SMOKE,
                EntityStateRole.BATTERY_LEVEL,
            },
        )
        self.assertEqual(
            resolution.extras,
            { EntityStateRole.SMOKE, EntityStateRole.BATTERY_LEVEL },
        )

    def test_no_fallback_for_context_raises( self ):
        self._register( _make_panel(
            name = 'fallback',
            entity_type = None,
            display_contexts = { DisplayContext.MODAL },
        ) )
        with self.assertRaises( RuntimeError ):
            StatePanelDispatcher.resolve_panel(
                entity_type = EntityType.THERMOSTAT,
                display_context = DisplayContext.GRID,
                present_roles = set(),
            )


class TestProductionPanelDiscovery( BaseTestCase ):
    """End-to-end check that the panel.py modules under
    ``hi.apps.entity.state_panels`` are wired up: each existing panel
    type resolves to a panel for each display context."""

    EXPECTED_TYPED_PANELS = {
        (EntityType.THERMOSTAT, DisplayContext.MODAL): 'thermostat_modal',
        (EntityType.THERMOSTAT, DisplayContext.LIST): 'thermostat_list',
        (EntityType.THERMOSTAT, DisplayContext.GRID): 'thermostat_grid',
        (EntityType.SMOKE_DETECTOR, DisplayContext.MODAL): 'smoke_detector_modal',
        (EntityType.SMOKE_DETECTOR, DisplayContext.LIST): 'smoke_detector_list',
        (EntityType.SMOKE_DETECTOR, DisplayContext.GRID): 'smoke_detector_grid',
        (EntityType.CAMERA, DisplayContext.MODAL): 'camera_modal',
        (EntityType.CAMERA, DisplayContext.LIST): 'camera_list',
        (EntityType.CAMERA, DisplayContext.GRID): 'camera_grid',
    }

    EXPECTED_FALLBACK_PANELS = {
        DisplayContext.MODAL: 'fallback_modal',
        DisplayContext.LIST: 'fallback_list',
        DisplayContext.GRID: 'fallback_grid',
    }

    def test_typed_panels_resolve_with_required_roles( self ):
        thermostat_present_roles = { EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE }
        smoke_present_roles = { EntityStateRole.SMOKE }
        for ( entity_type, ctx ), expected_name in self.EXPECTED_TYPED_PANELS.items():
            if entity_type == EntityType.THERMOSTAT:
                present_roles = thermostat_present_roles
            elif entity_type == EntityType.SMOKE_DETECTOR:
                present_roles = smoke_present_roles
            else:
                present_roles = set()
            resolution = StatePanelDispatcher.resolve_panel(
                entity_type = entity_type,
                display_context = ctx,
                present_roles = present_roles,
            )
            self.assertEqual(
                resolution.panel.name, expected_name,
                msg = f'{entity_type.name}/{ctx.name}',
            )

    def test_unknown_entity_type_falls_back( self ):
        for ctx, expected_name in self.EXPECTED_FALLBACK_PANELS.items():
            resolution = StatePanelDispatcher.resolve_panel(
                entity_type = EntityType.OTHER,
                display_context = ctx,
                present_roles = set(),
            )
            self.assertEqual( resolution.panel.name, expected_name )

    def test_typed_panel_falls_back_when_required_role_absent( self ):
        # Thermostat with no roles -> required THERMOSTAT_CURRENT_TEMPERATURE
        # is missing, so dispatch falls through to fallback.
        resolution = StatePanelDispatcher.resolve_panel(
            entity_type = EntityType.THERMOSTAT,
            display_context = DisplayContext.MODAL,
            present_roles = set(),
        )
        self.assertEqual( resolution.panel.name, 'fallback_modal' )


class TestDiscoveryErrorHandling( BaseTestCase ):

    def setUp( self ):
        super().setUp()
        self._registry_snapshot = EntityStatePanelRegistry().snapshot_for_tests()

    def tearDown( self ):
        EntityStatePanelRegistry().restore_for_tests( self._registry_snapshot )
        super().tearDown()

    def test_broken_panel_module_does_not_abort_discovery( self ):
        """If one panel.py raises at import, discover() should log and
        continue rather than poisoning Django startup."""
        from unittest.mock import patch
        registry = EntityStatePanelRegistry()
        registry.restore_for_tests( ( {}, False ) )

        with patch(
            'hi.apps.entity.state_panel_registry.importlib.import_module',
            side_effect = lambda name: (
                ( _ for _ in () ).throw( RuntimeError( 'boom' ) )
                if name.endswith( '.thermostat.panel' )
                else __import__( name, fromlist = [ '*' ] )
            ),
        ):
            registry.discover()

        # The broken panel is skipped, but other panels still register.
        all_names = { p.name for p in registry.all_panels() }
        self.assertIn( 'fallback_modal', all_names )
        # Thermostat module was the one we broke; its panels are absent.
        self.assertNotIn( 'thermostat_modal', all_names )


class TestIncludePanelTag( BaseTestCase ):

    def test_panel_context_keys_override_parent_context_keys( self ):
        """The {% include_panel %} tag must merge ``panel_context`` over
        the parent context so a panel template sees the panel-filtered
        values, not whatever the wrapper happened to define."""
        from django.template import Context, Template
        from hi.apps.entity.state_panel_dispatch import EntityStatePanelData
        from unittest.mock import Mock

        # A tiny inline template registered via Django's loaders is fussy;
        # easier to mock the loader resolution.
        panel_data = EntityStatePanelData(
            entity_display_data = Mock(),
            panel_template      = 'fixtures/test_include_panel.html',
            panel_context       = { 'shared_var': 'from-panel-context' },
        )
        from unittest.mock import patch
        rendered = None
        with patch(
            'hi.apps.entity.templatetags.state_panel_tags.get_template'
        ) as mock_get_template:
            mock_get_template.return_value.render.return_value = 'ok'
            mock_get_template.return_value.render.side_effect = (
                lambda flat, request = None: f'shared_var={flat.get("shared_var")}'
            )
            t = Template(
                '{% load state_panel_tags %}'
                '{% include_panel panel_data %}'
            )
            rendered = t.render( Context( {
                'panel_data': panel_data,
                'shared_var': 'from-parent-context',
            } ) )
        self.assertEqual( rendered, 'shared_var=from-panel-context' )
