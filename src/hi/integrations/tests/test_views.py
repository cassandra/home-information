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

    def get_description(self):
        return self._description

    def get_result_title(self):
        return 'Test Sync Result'

    def sync(self):
        from hi.apps.common.processing_result import ProcessingResult
        self.sync_called = True
        return ProcessingResult(
            title='Test Sync Result',
            message_list=['Synced.'],
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
    Framework pre-sync confirmation modal. Renders integration health,
    synchronizer description, and Sync / Not now actions; 404s when
    the integration does not provide a synchronizer.
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
