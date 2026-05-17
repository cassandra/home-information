import logging

from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType
from hi.apps.entity.state_panel_base import EntityStatusPanel
from hi.apps.entity.state_panel_dispatch import resolve_panel
from hi.apps.entity.state_panel_registry import EntityStatusPanelRegistry
from hi.testing.base_test_case import BaseTestCase


logging.disable( logging.CRITICAL )


def _make_panel( **overrides ) -> EntityStatusPanel:
    """Build an EntityStatusPanel with sensible defaults for testing.
    Only the attributes the test cares about need to be passed."""
    defaults = dict(
        name             = 'p',
        display_contexts = { DisplayContext.MODAL },
        priority         = 10,
        template_name    = 'entity/state_panels/p/panel.html',
    )
    defaults.update( overrides )
    return EntityStatusPanel( **defaults )


class TestEntityStatusPanelValidation( BaseTestCase ):

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


class TestEntityStatusPanelRegistry( BaseTestCase ):

    def setUp( self ):
        super().setUp()
        self._registry_snapshot = EntityStatusPanelRegistry().snapshot_for_tests()
        EntityStatusPanelRegistry().reset_for_tests()

    def tearDown( self ):
        EntityStatusPanelRegistry().restore_for_tests( self._registry_snapshot )
        super().tearDown()

    def test_register_adds_panel( self ):
        registry = EntityStatusPanelRegistry()
        panel = _make_panel( name = 'alpha' )
        registry.register( panel )
        self.assertIs( registry.get_by_name( 'alpha' ), panel )
        self.assertIn( panel, registry.all_panels() )

    def test_re_registering_same_instance_is_idempotent( self ):
        registry = EntityStatusPanelRegistry()
        panel = _make_panel( name = 'alpha' )
        registry.register( panel )
        registry.register( panel )
        self.assertEqual( len( registry.all_panels() ), 1 )

    def test_duplicate_name_different_instance_rejected( self ):
        registry = EntityStatusPanelRegistry()
        registry.register( _make_panel( name = 'alpha' ) )
        with self.assertRaises( RuntimeError ):
            registry.register( _make_panel( name = 'alpha' ) )


class TestResolvePanel( BaseTestCase ):

    def setUp( self ):
        super().setUp()
        self._registry_snapshot = EntityStatusPanelRegistry().snapshot_for_tests()
        EntityStatusPanelRegistry().reset_for_tests()

    def tearDown( self ):
        EntityStatusPanelRegistry().restore_for_tests( self._registry_snapshot )
        super().tearDown()

    def _register( self, panel ):
        EntityStatusPanelRegistry().register( panel )
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
        resolution = resolve_panel(
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
        resolution = resolve_panel(
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
        resolution = resolve_panel(
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
        resolution = resolve_panel(
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
        resolution = resolve_panel(
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
        resolution = resolve_panel(
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
            resolve_panel(
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
            resolution = resolve_panel(
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
            resolution = resolve_panel(
                entity_type = EntityType.OTHER,
                display_context = ctx,
                present_roles = set(),
            )
            self.assertEqual( resolution.panel.name, expected_name )

    def test_typed_panel_falls_back_when_required_role_absent( self ):
        # Thermostat with no roles -> required THERMOSTAT_CURRENT_TEMPERATURE
        # is missing, so dispatch falls through to fallback.
        resolution = resolve_panel(
            entity_type = EntityType.THERMOSTAT,
            display_context = DisplayContext.MODAL,
            present_roles = set(),
        )
        self.assertEqual( resolution.panel.name, 'fallback_modal' )
