"""
View tests for Integration lifecycle actions.
"""

import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.enums import IntegrationAttributeType, IntegrationDisableMode
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.models import Integration
from hi.integrations.transient_models import IntegrationMetaData
from hi.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class _PauseResumeTestAttributeType(IntegrationAttributeType):
    TEST_ATTR = ('Test Attribute', 'Test description', AttributeValueType.TEXT, {}, True, True, 'default')


class _PauseResumeTestGateway(IntegrationGateway):

    def __init__(self, integration_id='pause_resume_view_test'):
        self.integration_id = integration_id

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label='Pause/Resume Test Integration',
            attribute_type=_PauseResumeTestAttributeType,
            allow_entity_deletion=True,
        )

    def get_manage_view_pane(self):
        return Mock()

    def get_monitor(self):
        return Mock()

    def get_controller(self):
        return Mock()


class PauseResumeViewTests(SyncViewTestCase):
    """
    View tests for the Pause and Resume lifecycle actions.

    Only covers behavior that encodes app-critical decisions:
      - The view delegates to the correct manager method.
      - The is_enabled guard prevents pause/resume on a not-enabled integration.
    """

    def setUp(self):
        super().setUp()
        IntegrationManager().reset_for_testing()

        self.integration = Integration.objects.create(
            integration_id='pause_resume_view_test',
            is_enabled=True,
            is_paused=False,
        )
        self.integration_data = IntegrationData(
            integration_gateway=_PauseResumeTestGateway('pause_resume_view_test'),
            integration=self.integration,
        )
        IntegrationManager()._integration_data_map['pause_resume_view_test'] = self.integration_data

    def test_pause_view_delegates_to_manager(self):
        url = reverse('integrations_pause', kwargs={'integration_id': 'pause_resume_view_test'})
        with patch.object(IntegrationManager, 'pause_integration') as mock_pause:
            response = self.client.post(url)

        self.assertSuccessResponse(response)
        mock_pause.assert_called_once()
        call_kwargs = mock_pause.call_args.kwargs
        self.assertEqual(call_kwargs['integration_data'].integration_id, 'pause_resume_view_test')

    def test_resume_view_delegates_to_manager(self):
        url = reverse('integrations_resume', kwargs={'integration_id': 'pause_resume_view_test'})
        with patch.object(IntegrationManager, 'resume_integration') as mock_resume:
            response = self.client.post(url)

        self.assertSuccessResponse(response)
        mock_resume.assert_called_once()
        call_kwargs = mock_resume.call_args.kwargs
        self.assertEqual(call_kwargs['integration_data'].integration_id, 'pause_resume_view_test')

    def test_pause_view_rejects_not_enabled_integration(self):
        self.integration.is_enabled = False
        self.integration.save()

        url = reverse('integrations_pause', kwargs={'integration_id': 'pause_resume_view_test'})
        with patch.object(IntegrationManager, 'pause_integration') as mock_pause:
            response = self.client.post(url)

        self.assertErrorResponse(response)
        mock_pause.assert_not_called()

    def test_resume_view_rejects_not_enabled_integration(self):
        self.integration.is_enabled = False
        self.integration.save()

        url = reverse('integrations_resume', kwargs={'integration_id': 'pause_resume_view_test'})
        with patch.object(IntegrationManager, 'resume_integration') as mock_resume:
            response = self.client.post(url)

        self.assertErrorResponse(response)
        mock_resume.assert_not_called()


class RemoveViewTests(SyncViewTestCase):
    """
    View tests for the Remove confirmation dialog.

    Covers behavior that encodes real decisions:
      - POST dispatches the correct IntegrationDisableMode to the manager.
      - Missing/invalid mode falls back to SAFE (form-facing safety default).
      - Not-enabled integrations are rejected.
    """

    INTEGRATION_ID = 'remove_view_test'

    def setUp(self):
        super().setUp()
        IntegrationManager().reset_for_testing()

        self.integration = Integration.objects.create(
            integration_id=self.INTEGRATION_ID,
            is_enabled=True,
            is_paused=False,
        )
        integration_data = IntegrationData(
            integration_gateway=_PauseResumeTestGateway(self.INTEGRATION_ID),
            integration=self.integration,
        )
        IntegrationManager()._integration_data_map[self.INTEGRATION_ID] = integration_data

    def _url(self):
        return reverse('integrations_disable', kwargs={'integration_id': self.INTEGRATION_ID})

    def test_post_with_mode_safe_dispatches_safe(self):
        with patch.object(IntegrationManager, 'disable_integration') as mock_disable:
            response = self.client.post(self._url(), {'mode': IntegrationDisableMode.SAFE.name})

        self.assertSuccessResponse(response)
        mock_disable.assert_called_once()
        self.assertEqual(mock_disable.call_args.kwargs['mode'], IntegrationDisableMode.SAFE)

    def test_post_with_mode_all_dispatches_all(self):
        with patch.object(IntegrationManager, 'disable_integration') as mock_disable:
            response = self.client.post(self._url(), {'mode': IntegrationDisableMode.ALL.name})

        self.assertSuccessResponse(response)
        mock_disable.assert_called_once()
        self.assertEqual(mock_disable.call_args.kwargs['mode'], IntegrationDisableMode.ALL)

    def test_post_with_missing_mode_defaults_to_safe(self):
        """Tampered / missing mode must not escalate to ALL."""
        with patch.object(IntegrationManager, 'disable_integration') as mock_disable:
            response = self.client.post(self._url(), {})

        self.assertSuccessResponse(response)
        self.assertEqual(mock_disable.call_args.kwargs['mode'], IntegrationDisableMode.SAFE)

    def test_post_with_unknown_mode_defaults_to_safe(self):
        """Tampered / unknown mode must not escalate to ALL."""
        with patch.object(IntegrationManager, 'disable_integration') as mock_disable:
            response = self.client.post(self._url(), {'mode': 'NUKE'})

        self.assertSuccessResponse(response)
        self.assertEqual(mock_disable.call_args.kwargs['mode'], IntegrationDisableMode.SAFE)

    def test_post_rejects_not_enabled_integration(self):
        self.integration.is_enabled = False
        self.integration.save()

        with patch.object(IntegrationManager, 'disable_integration') as mock_disable:
            response = self.client.post(self._url(), {'mode': IntegrationDisableMode.SAFE.name})

        self.assertErrorResponse(response)
        mock_disable.assert_not_called()


# --------------------------------------------------------------------------
# Pre-sync confirmation modal + framework Sync view tests
# --------------------------------------------------------------------------


class _SyncTestSynchronizer:
    """
    Stand-in synchronizer for pre-sync / sync view tests. Stays
    intentionally minimal (does NOT extend IntegrationSynchronizer) to
    avoid acquiring the real lock or running framework retry logic in
    unit tests; the views only need methods the framework actually
    calls on it.
    """
    def __init__(self, description='Test integration sync description.'):
        self._description = description
        self.sync_called = False

    def get_description(self, is_initial_import):
        self.last_is_initial_import = is_initial_import
        return self._description

    def get_result_title(self, is_initial_import):
        return 'Test Sync Result'

    def sync(self, is_initial_import=False):
        from hi.integrations.sync_result import IntegrationSyncResult
        self.sync_called = True
        return IntegrationSyncResult(
            title='Test Sync Result',
            info_list=['Synced.'],
        )


class _SyncTestHealthStatusProvider:
    @property
    def health_status(self):
        # The pre-sync template renders the health badge partial; tests
        # don't need a real provider, just a stand-in that returns
        # something safe to traverse from a Django template.
        return Mock(status=Mock(name='HEALTHY'), is_healthy=True)


class _SyncCapableGateway(IntegrationGateway):
    """Gateway that provides a synchronizer + health provider."""

    def __init__(self, integration_id='sync_view_test', synchronizer=None):
        self.integration_id = integration_id
        self._synchronizer = (
            synchronizer if synchronizer is not None else _SyncTestSynchronizer()
        )

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label='Sync View Test Integration',
            attribute_type=_PauseResumeTestAttributeType,
            allow_entity_deletion=True,
        )

    def get_manage_view_pane(self):
        return Mock()

    def get_monitor(self):
        return Mock()

    def get_controller(self):
        return Mock()

    def get_synchronizer(self):
        return self._synchronizer

    def get_health_status_provider(self):
        return _SyncTestHealthStatusProvider()


class _SyncIncapableGateway(IntegrationGateway):
    """Gateway whose integration does NOT support sync."""

    def __init__(self, integration_id='no_sync_view_test'):
        self.integration_id = integration_id

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label='No Sync Test Integration',
            attribute_type=_PauseResumeTestAttributeType,
            allow_entity_deletion=True,
        )

    def get_manage_view_pane(self):
        return Mock()

    def get_monitor(self):
        return Mock()

    def get_controller(self):
        return Mock()


class PreSyncViewTests(SyncViewTestCase):
    """
    Framework pre-sync confirmation modal. Renders the synchronizer
    description plus IMPORT/REFRESH and (first-time only) REVIEW
    CONFIG actions; 404s when the integration does not provide a
    synchronizer.
    """

    INTEGRATION_ID = 'sync_view_test'

    def setUp(self):
        super().setUp()
        IntegrationManager().reset_for_testing()

        self.integration = Integration.objects.create(
            integration_id=self.INTEGRATION_ID,
            is_enabled=True,
            is_paused=False,
        )
        self.synchronizer = _SyncTestSynchronizer(
            description='HASS-flavored fake description.'
        )
        self.gateway = _SyncCapableGateway(
            integration_id=self.INTEGRATION_ID,
            synchronizer=self.synchronizer,
        )
        IntegrationManager()._integration_data_map[self.INTEGRATION_ID] = IntegrationData(
            integration_gateway=self.gateway,
            integration=self.integration,
        )

    def _url(self):
        return reverse(
            'integrations_pre_sync',
            kwargs={'integration_id': self.INTEGRATION_ID},
        )

    def test_get_returns_modal_with_description(self):
        response = self.client.get(self._url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        self.assertIn('HASS-flavored fake description.', body)

    def test_get_404s_when_integration_has_no_synchronizer(self):
        # Replace the integration_data with one whose gateway returns
        # None from get_synchronizer.
        IntegrationManager()._integration_data_map[self.INTEGRATION_ID] = IntegrationData(
            integration_gateway=_SyncIncapableGateway(self.INTEGRATION_ID),
            integration=self.integration,
        )
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 404)

    def test_review_config_action_present_on_initial_import(self):
        """REVIEW CONFIG button is shown only on the first-time path.

        With no entities for this integration, is_initial_import=True
        and the REVIEW CONFIG affordance must appear so the user can
        return to the configure step.
        """
        response = self.client.get(self._url())
        self.assertSuccessResponse(response)
        self.assertIn('REVIEW CONFIG', response.content.decode())

    def test_review_config_action_absent_after_initial_import(self):
        """REVIEW CONFIG is omitted on the manage-page entry path.

        With at least one entity already imported, is_initial_import
        is False; the user came from the manage page and CANCEL takes
        them back, so REVIEW CONFIG is unnecessary.
        """
        from hi.apps.entity.enums import EntityType
        from hi.apps.entity.models import Entity
        Entity.objects.create(
            integration_id=self.INTEGRATION_ID,
            integration_name='already_imported',
            name='Already Imported',
            entity_type_str=EntityType.default_value(),
        )
        response = self.client.get(self._url())
        self.assertSuccessResponse(response)
        self.assertNotIn('REVIEW CONFIG', response.content.decode())


class SyncViewTests(SyncViewTestCase):
    """
    Framework Sync view: POSTs invoke the synchronizer's sync() and
    return the result modal. 404s when the integration does not
    provide a synchronizer.
    """

    INTEGRATION_ID = 'sync_view_test'

    def setUp(self):
        super().setUp()
        IntegrationManager().reset_for_testing()

        self.integration = Integration.objects.create(
            integration_id=self.INTEGRATION_ID,
            is_enabled=True,
            is_paused=False,
        )
        self.synchronizer = _SyncTestSynchronizer()
        self.gateway = _SyncCapableGateway(
            integration_id=self.INTEGRATION_ID,
            synchronizer=self.synchronizer,
        )
        IntegrationManager()._integration_data_map[self.INTEGRATION_ID] = IntegrationData(
            integration_gateway=self.gateway,
            integration=self.integration,
        )

    def _url(self):
        return reverse(
            'integrations_sync',
            kwargs={'integration_id': self.INTEGRATION_ID},
        )

    def test_post_invokes_synchronizer_sync(self):
        response = self.client.post(self._url())
        self.assertSuccessResponse(response)
        self.assertTrue(self.synchronizer.sync_called)

    def test_post_404s_when_integration_has_no_synchronizer(self):
        IntegrationManager()._integration_data_map[self.INTEGRATION_ID] = IntegrationData(
            integration_gateway=_SyncIncapableGateway(self.INTEGRATION_ID),
            integration=self.integration,
        )
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, 404)


# --------------------------------------------------------------------------
# IntegrationEnableView tests for the Review Config (post-enable) path
# --------------------------------------------------------------------------


class EnableViewReviewConfigTests(SyncViewTestCase):
    """
    IntegrationEnableView accepts both first-time Configure and Review
    Config (post-enable). The button label switches with state, and
    the post-enable GET no longer 400s.
    """

    INTEGRATION_ID = 'enable_review_view_test'

    def setUp(self):
        super().setUp()
        IntegrationManager().reset_for_testing()
        self.integration = Integration.objects.create(
            integration_id=self.INTEGRATION_ID,
            is_enabled=True,
            is_paused=False,
        )
        self.gateway = _SyncCapableGateway(integration_id=self.INTEGRATION_ID)
        IntegrationManager()._integration_data_map[self.INTEGRATION_ID] = IntegrationData(
            integration_gateway=self.gateway,
            integration=self.integration,
        )

    def _url(self):
        return reverse(
            'integrations_enable',
            kwargs={'integration_id': self.INTEGRATION_ID},
        )

    def test_get_post_enable_does_not_400(self):
        """Removed is_enabled BadRequest: GET on an enabled integration
        must return 200 so Review Config can re-render the form."""
        response = self.client.get(self._url())
        self.assertSuccessResponse(response)

    def test_get_post_enable_renders_update_button_label(self):
        """Review-mode GET uses 'UPDATE' as the action label, not 'CONFIGURE'."""
        response = self.client.get(self._url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        self.assertIn('UPDATE', body)
        self.assertNotIn('CONFIGURE', body)

    def test_get_post_enable_renders_continue_action(self):
        """Review-mode GET replaces the dismiss CANCEL with a CONTINUE
        action that returns to the pre-sync modal. Without this swap a
        user reviewing config with no changes has only SAVE (which
        re-saves) or CANCEL (which aborts the whole sync flow) — both
        wrong for the read-only review path."""
        response = self.client.get(self._url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        self.assertIn('CONTINUE', body)
        # Cancel button has id="hi-modal-cancel"; its absence in review
        # mode is what we're pinning here.
        self.assertNotIn('hi-modal-cancel', body)
        # The CONTINUE action must point at the pre-sync URL.
        self.assertIn(
            reverse('integrations_pre_sync', kwargs={'integration_id': self.INTEGRATION_ID}),
            body,
        )

    def test_get_first_time_renders_configure_button_label(self):
        """First-time GET (is_enabled=False) keeps the original
        'CONFIGURE' label and the dismiss CANCEL."""
        self.integration.is_enabled = False
        self.integration.save()
        response = self.client.get(self._url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        self.assertIn('CONFIGURE', body)
        self.assertIn('hi-modal-cancel', body)
        self.assertNotIn('CONTINUE', body)


# --------------------------------------------------------------------------
# Placement + post-placement + refine (Phase 3) tests
# --------------------------------------------------------------------------


class _PlacementTestSynchronizer:
    """Synchronizer stub that returns a populated IntegrationSyncResult.

    Three entities placed across two groups + one ungrouped item:
    enough to exercise group default, drill-down override, and
    ungrouped per-item paths.
    """
    def __init__(self, sync_result):
        self._sync_result = sync_result
        self.sync_called = False

    def get_description(self, is_initial_import):
        return None

    def get_result_title(self, is_initial_import):
        return 'Placement Test'

    def sync(self, is_initial_import=False):
        self.sync_called = True
        return self._sync_result


class _PlacementTestGateway(IntegrationGateway):
    """Placement gateway with a synchronizer + minimal stubs."""

    def __init__(self, integration_id, synchronizer):
        self.integration_id = integration_id
        self._synchronizer = synchronizer

    def get_metadata(self):
        return IntegrationMetaData(
            integration_id=self.integration_id,
            label='Placement Test',
            attribute_type=_PauseResumeTestAttributeType,
            allow_entity_deletion=True,
        )

    def get_manage_view_pane(self):
        return Mock()

    def get_monitor(self):
        return Mock()

    def get_controller(self):
        return Mock()

    def get_synchronizer(self):
        return self._synchronizer

    def get_health_status_provider(self):
        return Mock()


class PlacementFlowTests(SyncViewTestCase):
    """End-to-end placement flow: sync → placement modal → apply →
    post-placement modal."""

    INTEGRATION_ID = 'placement_test'

    def setUp(self):
        super().setUp()
        IntegrationManager().reset_for_testing()

        from hi.apps.entity.entity_placement import (
            EntityPlacementGroup,
            EntityPlacementInput,
            EntityPlacementItem,
        )
        from hi.apps.entity.enums import EntityType
        from hi.apps.entity.models import Entity
        from hi.apps.location.models import Location, LocationView
        from hi.integrations.sync_result import IntegrationSyncResult

        self.integration = Integration.objects.create(
            integration_id=self.INTEGRATION_ID,
            is_enabled=True,
            is_paused=False,
        )
        self.location = Location.objects.create(
            name='Test Location',
            svg_view_box_str='0 0 1000 1000',
        )
        self.view_a = LocationView.objects.create(
            location=self.location, name='Kitchen', order_id=1,
            svg_view_box_str='0 0 1000 1000',
            svg_rotate=0, svg_style_name_str='COLOR',
            location_view_type_str='DEFAULT',
        )
        self.view_b = LocationView.objects.create(
            location=self.location, name='Living Room', order_id=2,
            svg_view_box_str='0 0 1000 1000',
            svg_rotate=0, svg_style_name_str='COLOR',
            location_view_type_str='DEFAULT',
        )

        self.entity_a = Entity.objects.create(
            name='Cam 1',
            entity_type_str=str(EntityType.CAMERA),
            integration_id=self.INTEGRATION_ID,
            integration_name='cam_1',
        )
        self.entity_b = Entity.objects.create(
            name='Cam 2',
            entity_type_str=str(EntityType.CAMERA),
            integration_id=self.INTEGRATION_ID,
            integration_name='cam_2',
        )
        self.entity_c = Entity.objects.create(
            name='Light 1',
            entity_type_str=str(EntityType.LIGHT),
            integration_id=self.INTEGRATION_ID,
            integration_name='light_1',
        )
        self.ungrouped_entity = Entity.objects.create(
            name='Ungrouped Thing',
            entity_type_str=str(EntityType.OTHER),
            integration_id=self.INTEGRATION_ID,
            integration_name='thing_1',
        )

        self.sync_result = IntegrationSyncResult(
            title='Placement Test',
            created_list=['Cam 1', 'Cam 2', 'Light 1', 'Ungrouped Thing'],
            placement_input=EntityPlacementInput(
                groups=[
                    EntityPlacementGroup(
                        label='Cameras',
                        items=[
                            EntityPlacementItem(key='placement_test:cam_1', label='Cam 1', entity=self.entity_a),
                            EntityPlacementItem(key='placement_test:cam_2', label='Cam 2', entity=self.entity_b),
                        ],
                    ),
                    EntityPlacementGroup(
                        label='Lights',
                        items=[
                            EntityPlacementItem(key='placement_test:light_1', label='Light 1', entity=self.entity_c),
                        ],
                    ),
                ],
                ungrouped_items=[
                    EntityPlacementItem(
                        key='placement_test:thing_1',
                        label='Ungrouped Thing',
                        entity=self.ungrouped_entity,
                    ),
                ],
            ),
        )

        self.synchronizer = _PlacementTestSynchronizer(sync_result=self.sync_result)
        self.gateway = _PlacementTestGateway(
            integration_id=self.INTEGRATION_ID, synchronizer=self.synchronizer,
        )
        IntegrationManager()._integration_data_map[self.INTEGRATION_ID] = IntegrationData(
            integration_gateway=self.gateway, integration=self.integration,
        )

    def _sync_url(self):
        return reverse(
            'integrations_sync', kwargs={'integration_id': self.INTEGRATION_ID},
        )

    def _placement_url(self):
        # GET renders / POST processes — same URL after the
        # GET+POST view consolidation.
        return reverse(
            'integrations_placement',
            kwargs={'integration_id': self.INTEGRATION_ID},
        )

    def test_sync_renders_result_modal_with_place_items_cta(self):
        """Sync that produced new entities → sync result modal with
        a primary 'Place N items' CTA pointing at the placement
        GET endpoint. The placement is no longer rendered directly
        from the sync POST response — placement is opt-in."""
        response = self.client.post(self._sync_url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        # Result-modal markers (NOT placement markers).
        # Hero copy is is_initial_import-aware. Test setup leaves
        # Entity rows in the DB so the sync view sees this as a
        # Refresh, not an Initial Import.
        self.assertIn('Refresh complete', body)
        self.assertIn('Place Later', body)
        self.assertIn('Place 4 new items', body)
        self.assertIn(self._placement_url(), body)
        # No placement artifacts in the response — operator must
        # click the CTA to reach the placement.
        self.assertNotIn('APPLY', body)

    def test_sync_renders_result_modal_without_cta_when_no_creates(self):
        """Sync result with no created entities → result modal with
        no 'Place items' CTA. Single centered OK is the only footer
        action (matches the project's 'acknowledge info, dismiss'
        single-button convention)."""
        from hi.integrations.sync_result import IntegrationSyncResult
        self.synchronizer._sync_result = IntegrationSyncResult(title='Empty')
        response = self.client.post(self._sync_url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        self.assertIn('hi-modal-ok', body)
        self.assertNotIn('Place ', body)
        self.assertNotIn('APPLY', body)

    def test_sync_renders_result_modal_with_updates_and_removes_visible(self):
        """Update/remove signal is no longer swallowed by the
        placement when there are also creates — every change kind
        is enumerated in the result modal even though the modal
        ultimately routes the operator to placement."""
        from hi.integrations.sync_result import IntegrationSyncResult
        self.synchronizer._sync_result = IntegrationSyncResult(
            title='Mixed Result',
            created_list=['Brand New Light'],
            updated_list=['Old Name → New Name'],
            removed_list=['Stale Sensor'],
            placement_input=self.sync_result.placement_input,
        )
        response = self.client.post(self._sync_url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        # All three categories visible in the result.
        self.assertIn('Brand New Light', body)
        self.assertIn('Old Name → New Name', body)
        self.assertIn('Stale Sensor', body)
        # And the CTA still routes to the placement.
        self.assertIn('Place 1 new item', body)

    def test_placement_top_inherits_to_groups_and_entities(self):
        """Top view chosen, groups + entities at default → every
        entity goes to the top view."""
        from hi.apps.entity.models import EntityView
        response = self.client.post(self._placement_url(), {
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id), str(self.entity_b.id)],
            'all_group_1_entity_ids': [str(self.entity_c.id)],
            'ungrouped_entity_ids': [str(self.ungrouped_entity.id)],
        })
        self.assertSuccessResponse(response)
        for entity in [self.entity_a, self.entity_b, self.entity_c, self.ungrouped_entity]:
            self.assertTrue(EntityView.objects.filter(
                entity=entity, location_view=self.view_a).exists())

    def test_placement_group_overrides_top(self):
        """Group view overrides top for entities in that group;
        other groups still inherit top."""
        from hi.apps.entity.models import EntityView
        response = self.client.post(self._placement_url(), {
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id), str(self.entity_b.id)],
            'all_group_1_entity_ids': [str(self.entity_c.id)],
            'group_view_0': f'view:{self.view_b.id}',  # Cameras → view_b
            # group_view_1 left blank → inherits view_a
        })
        self.assertSuccessResponse(response)
        self.assertTrue(EntityView.objects.filter(
            entity=self.entity_a, location_view=self.view_b).exists())
        self.assertTrue(EntityView.objects.filter(
            entity=self.entity_b, location_view=self.view_b).exists())
        self.assertTrue(EntityView.objects.filter(
            entity=self.entity_c, location_view=self.view_a).exists())

    def test_placement_drill_down_override_wins(self):
        """Per-entity override beats group default for that entity."""
        from hi.apps.entity.models import EntityView
        response = self.client.post(self._placement_url(), {
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id), str(self.entity_b.id)],
            'group_view_0': f'view:{self.view_a.id}',
            f'group_0_entity_{self.entity_b.id}_view': f'view:{self.view_b.id}',
        })
        self.assertSuccessResponse(response)
        self.assertTrue(EntityView.objects.filter(
            entity=self.entity_a, location_view=self.view_a).exists())
        self.assertTrue(EntityView.objects.filter(
            entity=self.entity_b, location_view=self.view_b).exists())
        self.assertFalse(EntityView.objects.filter(
            entity=self.entity_b, location_view=self.view_a).exists())

    def test_placement_skip_at_top_skips_everything(self):
        """top='' + groups inherit + entities inherit → all skipped."""
        from hi.apps.entity.models import EntityView
        response = self.client.post(self._placement_url(), {
            'top_view': '',
            'all_group_0_entity_ids': [str(self.entity_a.id)],
        })
        self.assertSuccessResponse(response)
        self.assertFalse(EntityView.objects.filter(entity=self.entity_a).exists())

    def test_placement_explicit_group_skip_overrides_top(self):
        """Top view chosen, group explicitly skipped → those entities
        don't get placed even though top has a view."""
        from hi.apps.entity.models import EntityView
        response = self.client.post(self._placement_url(), {
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id)],
            'group_view_0': '__skip__',
        })
        self.assertSuccessResponse(response)
        self.assertFalse(EntityView.objects.filter(entity=self.entity_a).exists())

    def test_placement_explicit_entity_skip_overrides_group(self):
        """Group inherits top, but specific entity is explicitly skipped."""
        from hi.apps.entity.models import EntityView
        response = self.client.post(self._placement_url(), {
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id), str(self.entity_b.id)],
            f'group_0_entity_{self.entity_a.id}_view': '__skip__',
        })
        self.assertSuccessResponse(response)
        self.assertFalse(EntityView.objects.filter(entity=self.entity_a).exists())
        self.assertTrue(EntityView.objects.filter(
            entity=self.entity_b, location_view=self.view_a).exists())

    def test_placement_new_view_creates_view_and_places_inherited_entities(self):
        """top='__new__' creates a fresh LocationView named after the
        integration; entities at default inherit it; existing-view
        overrides at group/entity levels still apply."""
        from hi.apps.entity.models import EntityView
        from hi.apps.location.models import LocationView
        before_view_ids = set(LocationView.objects.values_list('id', flat=True))
        response = self.client.post(self._placement_url(), {
            'top_view': '__new_view__',
            'all_group_0_entity_ids': [str(self.entity_a.id), str(self.entity_b.id)],
            'all_group_1_entity_ids': [str(self.entity_c.id)],
            'group_view_1': f'view:{self.view_a.id}',  # Lights → existing view
        })
        self.assertSuccessResponse(response)
        new_view_ids = (
            set(LocationView.objects.values_list('id', flat=True)) - before_view_ids
        )
        self.assertEqual(len(new_view_ids), 1)
        new_view = LocationView.objects.get(id=new_view_ids.pop())
        # Cameras inherited the new view.
        self.assertTrue(EntityView.objects.filter(
            entity=self.entity_a, location_view=new_view).exists())
        self.assertTrue(EntityView.objects.filter(
            entity=self.entity_b, location_view=new_view).exists())
        # Lights took the explicit existing-view override.
        self.assertTrue(EntityView.objects.filter(
            entity=self.entity_c, location_view=self.view_a).exists())
        # New view name = integration label.
        self.assertEqual(new_view.name, 'Placement Test')

    def test_post_placement_modal_renders_refine_for_primary_view(self):
        """The post-placement modal includes a REFINE button targeting
        the affected view, plus the view's name in the summary."""
        response = self.client.post(self._placement_url(), {
            'top_view': f'view:{self.view_a.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id)],
        })
        self.assertSuccessResponse(response)
        body = response.content.decode()
        self.assertIn('REFINE', body)
        self.assertIn('Kitchen', body)
        self.assertIn(reverse(
            'integrations_refine', kwargs={'location_view_id': self.view_a.id}
        ), body)

    def test_post_placement_primary_is_highest_count(self):
        """When multiple views are affected, primary REFINE points at
        the view with the most placed entities."""
        # Cameras (2) → view_b; Light (1) → view_a. view_b wins.
        response = self.client.post(self._placement_url(), {
            'top_view': f'view:{self.view_b.id}',
            'all_group_0_entity_ids': [str(self.entity_a.id), str(self.entity_b.id)],
            'all_group_1_entity_ids': [str(self.entity_c.id)],
            'group_view_1': f'view:{self.view_a.id}',  # Lights → view_a
        })
        self.assertSuccessResponse(response)
        body = response.content.decode()
        primary_refine_idx = body.find('REFINE')
        self.assertGreaterEqual(primary_refine_idx, 0)
        slice_after_refine = body[primary_refine_idx:primary_refine_idx + 200]
        self.assertIn('Living Room', slice_after_refine)


class PlacementDismissAndShowTests(SyncViewTestCase):
    """NOT NOW → dismiss-confirm modal → GO BACK → placement
    modal re-renders. Round-trip covers the dismiss + show views
    plus their hidden-input handshake."""

    INTEGRATION_ID = 'placement_test'

    def setUp(self):
        super().setUp()
        IntegrationManager().reset_for_testing()

        from hi.apps.entity.entity_placement import (
            EntityPlacementGroup,
            EntityPlacementInput,
            EntityPlacementItem,
        )
        from hi.apps.entity.enums import EntityType
        from hi.apps.entity.models import Entity
        from hi.apps.location.models import Location, LocationView
        from hi.integrations.sync_result import IntegrationSyncResult

        self.integration = Integration.objects.create(
            integration_id=self.INTEGRATION_ID,
            is_enabled=True,
            is_paused=False,
        )
        self.location = Location.objects.create(
            name='Test Location', svg_view_box_str='0 0 100 100',
        )
        self.view_a = LocationView.objects.create(
            location=self.location, name='Kitchen', order_id=1,
            svg_view_box_str='0 0 100 100', svg_rotate=0,
            svg_style_name_str='COLOR', location_view_type_str='DEFAULT',
        )
        self.entity_a = Entity.objects.create(
            name='Cam 1', entity_type_str=str(EntityType.CAMERA),
            integration_id=self.INTEGRATION_ID, integration_name='cam_1',
        )
        self.entity_b = Entity.objects.create(
            name='Cam 2', entity_type_str=str(EntityType.CAMERA),
            integration_id=self.INTEGRATION_ID, integration_name='cam_2',
        )

        self.sync_result = IntegrationSyncResult(
            title='Placement Test',
            placement_input=EntityPlacementInput(
                groups=[
                    EntityPlacementGroup(
                        label='Cameras',
                        items=[
                            EntityPlacementItem(key='placement_test:cam_1', label='Cam 1', entity=self.entity_a),
                            EntityPlacementItem(key='placement_test:cam_2', label='Cam 2', entity=self.entity_b),
                        ],
                    ),
                ],
            ),
        )
        self.synchronizer = _PlacementTestSynchronizer(sync_result=self.sync_result)
        # Stub group_entities_for_placement so the GET placement can
        # rebuild from unplaced entities.

        def group_for_placement(entities):
            items = [
                EntityPlacementItem(
                    key=f'placement_test:{e.integration_name}',
                    label=e.name, entity=e,
                )
                for e in entities
            ]
            if not items:
                return EntityPlacementInput()
            return EntityPlacementInput(
                groups=[EntityPlacementGroup(label='Cameras', items=items)],
            )
        self.synchronizer.group_entities_for_placement = group_for_placement

        self.gateway = _PlacementTestGateway(
            integration_id=self.INTEGRATION_ID, synchronizer=self.synchronizer,
        )
        IntegrationManager()._integration_data_map[self.INTEGRATION_ID] = IntegrationData(
            integration_gateway=self.gateway, integration=self.integration,
        )

    def _placement_url(self):
        return reverse(
            'integrations_placement',
            kwargs={'integration_id': self.INTEGRATION_ID},
        )

    def test_dismiss_renders_confirmation_with_placement_link(self):
        """The placement form's NOT NOW button (action=dismiss)
        routes back to the same placement URL where the view's
        POST handler renders the confirmation modal. GO BACK links
        to the placement GET with is_initial_import threaded
        through."""
        response = self.client.post(self._placement_url(), {
            'action': 'dismiss',
            'is_initial_import': '1',
        })
        self.assertSuccessResponse(response)
        body = response.content.decode()
        # Confirmation copy.
        self.assertIn('Items left unplaced', body)
        self.assertIn('GO BACK', body)
        self.assertIn('OK, PLACE LATER', body)
        # GO BACK targets the placement GET with is_initial_import=1.
        self.assertIn(self._placement_url() + '?is_initial_import=1', body)

    def test_placement_get_renders_from_unplaced_entities(self):
        """The GET placement queries entities for the integration
        that have no EntityView row, runs them through the
        synchronizer's group_entities_for_placement, and renders the
        placement modal."""
        response = self.client.get(self._placement_url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        # Placement rendered (APPLY button + entity ids in form).
        self.assertIn('APPLY', body)
        self.assertIn('Cameras', body)
        self.assertIn(f'value="{self.entity_a.id}"', body)
        self.assertIn(f'value="{self.entity_b.id}"', body)

    def test_placement_get_scopes_to_entity_ids_url_param(self):
        """When the URL carries ``entity_ids=...``, the placement
        filters the unplaced set to those ids — protects the sync-
        result CTA from showing pre-existing unplaced entities the
        operator didn't just import."""
        from hi.apps.entity.models import Entity
        from hi.apps.entity.enums import EntityType
        # Add a pre-existing unplaced entity that would otherwise
        # show up alongside cam_a/cam_b under the all-unplaced query.
        prior_unplaced = Entity.objects.create(
            name='Prior Unplaced Cam',
            entity_type_str=str(EntityType.CAMERA),
            integration_id=self.INTEGRATION_ID,
            integration_name='prior_unplaced',
        )
        # CTA URL targets only the two newly-imported cameras.
        scoped_url = (
            self._placement_url()
            + f'?entity_ids={self.entity_a.id},{self.entity_b.id}'
        )
        response = self.client.get(scoped_url)
        self.assertSuccessResponse(response)
        body = response.content.decode()
        self.assertIn(f'value="{self.entity_a.id}"', body)
        self.assertIn(f'value="{self.entity_b.id}"', body)
        # Pre-existing unplaced entity must NOT appear.
        self.assertNotIn(f'value="{prior_unplaced.id}"', body)
        self.assertNotIn('Prior Unplaced Cam', body)

    def test_placement_get_invalid_entity_ids_param_400s(self):
        """Tampered or malformed ``entity_ids`` fails loudly."""
        bad_url = self._placement_url() + '?entity_ids=1,abc'
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 400)

    def test_placement_get_renders_acknowledgement_when_no_unplaced(self):
        """When every entity for the integration is already placed,
        the GET placement renders the legacy result modal with
        a brief 'no items' message rather than an empty placement."""
        from hi.apps.entity.models import EntityView
        EntityView.objects.create(entity=self.entity_a, location_view=self.view_a)
        EntityView.objects.create(entity=self.entity_b, location_view=self.view_a)

        response = self.client.get(self._placement_url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        self.assertNotIn('APPLY', body)
        self.assertIn('No items left to place.', body)

    def test_placement_get_smart_default_picks_most_occupied_existing_view(self):
        """Refresh path: top dropdown is pre-selected to whichever
        existing target (view OR collection) holds the most entities
        for this integration. Entities in view_a outnumber any
        collection placement → top default = view_a."""
        from hi.apps.entity.models import EntityView
        from hi.apps.entity.models import Entity
        from hi.apps.entity.enums import EntityType
        # Place several entities (not from this placement's
        # placement_input — pre-existing 'placed' state is what
        # the smart default queries against).
        for index in range(3):
            placed = Entity.objects.create(
                name=f'Already Placed {index}',
                entity_type_str=str(EntityType.CAMERA),
                integration_id=self.INTEGRATION_ID,
                integration_name=f'placed_{index}',
            )
            EntityView.objects.create(
                entity=placed, location_view=self.view_a,
            )

        response = self.client.get(self._placement_url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        # Top dropdown is pre-selected to view_a.
        self.assertIn(
            f'value="view:{self.view_a.id}" selected', body,
        )

    def test_placement_get_smart_default_falls_back_to_dont_add_when_no_history(self):
        """Refresh path with no prior placements for this integration
        → top dropdown defaults to 'Don't place' (operator picks)."""
        response = self.client.get(self._placement_url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        # 'Don't place' option carries the selected attribute.
        self.assertIn('value="" selected', body)

    def test_placement_get_disambiguates_new_view_name_when_collision_exists(self):
        """When a LocationView already exists in the default Location
        with the integration's label, the '+ New view' option label
        shows the disambiguated name '(2)' so the operator's
        expectation matches the apply-time outcome."""
        from hi.apps.location.models import Location, LocationView
        # The PlacementDismissAndShowTests fixture builds a Location
        # named 'Test Location' with one view 'Kitchen'. Add a view
        # named 'Placement Test' (matching INTEGRATION_LABEL) to
        # collide with the new-view default.
        location = Location.objects.first()
        LocationView.objects.create(
            location=location, name='Placement Test', order_id=99,
            svg_view_box_str='0 0 100 100', svg_rotate=0,
            svg_style_name_str='COLOR', location_view_type_str='DEFAULT',
        )

        response = self.client.get(self._placement_url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        # New-view option label reflects disambiguation, not the raw
        # integration label.
        self.assertIn('+ New view: "Placement Test (2)"', body)

    def test_placement_get_inventory_preview_shows_group_counts(self):
        """When the placement_input has groups, the modal renders
        a single-line preview of label/count tuples beneath the
        top dropdown."""
        response = self.client.get(self._placement_url())
        self.assertSuccessResponse(response)
        body = response.content.decode()
        # The PlacementGetFlow fixture builds a single 'Cameras'
        # group with 2 items; the preview line lower-cases the
        # label and shows the count.
        self.assertIn('2 cameras', body)
        # Group rows are behind the disclosure (collapsed by
        # default) — the disclosure affordance is rendered.
        self.assertIn('Place differently', body)


class RefineViewTests(SyncViewTestCase):
    """The refine-edit-mode entry point flips view_mode and points the
    session at the chosen LocationView."""

    def setUp(self):
        super().setUp()
        from hi.apps.location.models import Location, LocationView
        location = Location.objects.create(
            name='Test', svg_view_box_str='0 0 100 100',
        )
        self.location_view = LocationView.objects.create(
            location=location, name='Refine View', order_id=1,
            svg_view_box_str='0 0 100 100',
            svg_rotate=0, svg_style_name_str='COLOR',
            location_view_type_str='DEFAULT',
        )

    def test_refine_redirects_to_location_view(self):
        from hi.enums import ViewMode
        response = self.client.get(reverse(
            'integrations_refine',
            kwargs={'location_view_id': self.location_view.id},
        ))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('location_view', kwargs={'location_view_id': self.location_view.id}),
        )
        # Session reflects edit mode + chosen view.
        self.assertEqual(self.client.session.get('view_mode'), str(ViewMode.EDIT))
        self.assertEqual(self.client.session.get('location_view_id'), self.location_view.id)

    def test_refine_404s_for_unknown_view(self):
        response = self.client.get(reverse(
            'integrations_refine', kwargs={'location_view_id': 99999},
        ))
        self.assertEqual(response.status_code, 404)
