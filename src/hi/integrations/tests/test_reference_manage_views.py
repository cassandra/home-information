"""View tests for the Content Sources management page.

Covers the GET-render, the Save/Enable submission flow (validate +
save + flip ``is_enabled`` on first activation), and the Disable
endpoint (flip ``is_enabled`` to False, credentials preserved).
"""
import logging

from django.urls import reverse

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.integrations.integration_data import IntegrationData
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationKey,
)
from hi.services.paperless.enums import PlAttributeType
from hi.services.paperless.integration import PaperlessGateway
from hi.services.paperless.pl_metadata import PaperlessMetaData
from hi.testing.view_test_base import ViewTestBase


logging.disable(logging.CRITICAL)


def _seed_manager( *integration_data ):
    """Seed the IntegrationManager singleton's in-memory data map.
    The manager is singletoned across the test process, so this
    explicit seed is the supported way for view tests to inject the
    integration data the views look up."""
    manager = IntegrationManager()
    manager._integration_data_map = {
        data.integration_id: data for data in integration_data
    }


def _make_attr( integration, attr_type, value ):
    attr = IntegrationAttribute.objects.create(
        integration = integration,
        name = attr_type.label,
        value = value,
        value_type_str = str(AttributeValueType.TEXT),
        attribute_type_str = str(AttributeType.PREDEFINED),
        is_editable = attr_type.is_editable,
        is_required = attr_type.is_required,
    )
    attr.integration_key = IntegrationKey(
        integration_id = PaperlessMetaData.integration_id,
        integration_name = str(attr_type),
    )
    attr.save()
    return attr


class TestReferenceManageGet( ViewTestBase ):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.integration = Integration.objects.create(
            integration_id = PaperlessMetaData.integration_id,
            is_enabled = False,
        )
        _seed_manager(IntegrationData(
            integration_gateway = PaperlessGateway(),
            integration = self.integration,
        ))

    def _url(self):
        return reverse(
            'integrations_reference_manage',
            kwargs = { 'integration_id': PaperlessMetaData.integration_id },
        )

    def test_renders_with_disabled_status(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Paperless-ngx', body)
        # Disabled-state hallmarks: badge + ENABLE button label.
        self.assertIn('DISABLED', body)
        self.assertIn('ENABLE', body)
        # No DISABLE button rendered when already disabled.
        self.assertNotIn('integrations_reference_deactivate', body)

    def test_renders_with_enabled_status(self):
        self.integration.is_enabled = True
        self.integration.save()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('ENABLED', body)
        # When enabled, the form button reverts to UPDATE and the
        # DISABLE button is wired in the header.
        self.assertIn('UPDATE', body)
        self.assertIn('DISABLE', body)


class TestReferenceManagePost( ViewTestBase ):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.integration = Integration.objects.create(
            integration_id = PaperlessMetaData.integration_id,
            is_enabled = False,
        )
        _seed_manager(IntegrationData(
            integration_gateway = PaperlessGateway(),
            integration = self.integration,
        ))
        # Required-by-framework predefined attribute rows. The
        # formset edits these in place rather than creating new
        # rows on submit.
        self.url_attr = _make_attr(self.integration, PlAttributeType.API_URL, '')
        self.token_attr = _make_attr(self.integration, PlAttributeType.API_TOKEN, '')

    def _url(self):
        return reverse(
            'integrations_reference_manage',
            kwargs = { 'integration_id': PaperlessMetaData.integration_id },
        )

    def _form_payload(self, api_url, api_token):
        # Formset wire shape: prefix is f'{owner_type}-{owner.id}'
        # (see ``AttributeItemEditContext.formset_prefix``). The
        # inline IntegrationAttribute formset wraps existing rows
        # by id; we re-post each row's name + value to keep the
        # formset valid.
        prefix = f'integration-{self.integration.id}'
        return {
            f'{prefix}-TOTAL_FORMS': '2',
            f'{prefix}-INITIAL_FORMS': '2',
            f'{prefix}-MIN_NUM_FORMS': '0',
            f'{prefix}-MAX_NUM_FORMS': '100',

            f'{prefix}-0-id': str(self.url_attr.id),
            f'{prefix}-0-name': self.url_attr.name,
            f'{prefix}-0-value': api_url,

            f'{prefix}-1-id': str(self.token_attr.id),
            f'{prefix}-1-name': self.token_attr.name,
            f'{prefix}-1-value': api_token,
        }

    def _patch_validate_access(self, success: bool, message: str = ''):
        from unittest.mock import patch
        result = (
            ConnectionTestResult.success() if success
            else ConnectionTestResult.failure(message or 'probe failed')
        )
        return patch(
            'hi.services.paperless.integration.PaperlessGateway.validate_access',
            return_value = result,
        )

    def test_save_with_valid_creds_enables_disabled_integration(self):
        with self._patch_validate_access(success = True):
            response = self.client.post(self._url(), data = self._form_payload(
                api_url = 'https://paperless.example.com/',
                api_token = 'good-token',
            ))

        self.integration.refresh_from_db()
        self.url_attr.refresh_from_db()
        self.token_attr.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.integration.is_enabled)
        self.assertEqual(self.url_attr.value, 'https://paperless.example.com/')
        self.assertEqual(self.token_attr.value, 'good-token')

    def test_save_on_already_enabled_keeps_enabled(self):
        # UPDATE flow: integration is enabled; save should keep
        # is_enabled=True and persist any credential changes.
        self.integration.is_enabled = True
        self.integration.save()
        self.url_attr.value = 'https://old.example.com/'
        self.url_attr.save()

        with self._patch_validate_access(success = True):
            response = self.client.post(self._url(), data = self._form_payload(
                api_url = 'https://new.example.com/',
                api_token = 'rotated-token',
            ))

        self.integration.refresh_from_db()
        self.url_attr.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.integration.is_enabled)
        self.assertEqual(self.url_attr.value, 'https://new.example.com/')

    def test_save_with_bad_access_does_not_save_or_enable(self):
        # Atomic semantics: failed probe blocks the save entirely.
        # Neither attributes nor is_enabled change. Operator sees
        # the access failure inline on the form (framework error
        # response renders the form again with errors).
        self.url_attr.value = 'https://old.example.com/'
        self.url_attr.save()

        with self._patch_validate_access(
                success = False, message = 'auth rejected',
        ):
            response = self.client.post(self._url(), data = self._form_payload(
                api_url = 'https://new.example.com/',
                api_token = 'bad-token',
            ))

        self.integration.refresh_from_db()
        self.url_attr.refresh_from_db()
        # Framework returns 400 on form errors (the antinode
        # response carries the re-rendered form for swap-in).
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.integration.is_enabled)
        self.assertEqual(self.url_attr.value, 'https://old.example.com/')

    def test_save_with_bad_access_when_enabled_keeps_old_state(self):
        # The (a) post-condition: an UPDATE-while-enabled with a bad
        # probe leaves the integration enabled with its previously
        # working creds. Nothing partially changes.
        self.integration.is_enabled = True
        self.integration.save()
        self.url_attr.value = 'https://old.example.com/'
        self.url_attr.save()

        with self._patch_validate_access(
                success = False, message = 'auth rejected',
        ):
            response = self.client.post(self._url(), data = self._form_payload(
                api_url = 'https://new.example.com/',
                api_token = 'rotated-token',
            ))

        self.integration.refresh_from_db()
        self.url_attr.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        # Still enabled, still old URL.
        self.assertTrue(self.integration.is_enabled)
        self.assertEqual(self.url_attr.value, 'https://old.example.com/')


class TestReferenceDisableAction( ViewTestBase ):
    """Disable rides the manage URL as an in-form action — the
    DISABLE button submits the surrounding attribute form with
    ``action=disable`` in the POST body, which the view dispatches
    on. No separate URL."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.integration = Integration.objects.create(
            integration_id = PaperlessMetaData.integration_id,
            is_enabled = True,
        )
        _seed_manager(IntegrationData(
            integration_gateway = PaperlessGateway(),
            integration = self.integration,
        ))

    def _url(self):
        return reverse(
            'integrations_reference_manage',
            kwargs = { 'integration_id': PaperlessMetaData.integration_id },
        )

    def test_disable_action_flips_is_enabled(self):
        response = self.client.post(self._url(), data = { 'action': 'disable' })
        self.assertEqual(response.status_code, 200)
        self.integration.refresh_from_db()
        self.assertFalse(self.integration.is_enabled)

    def test_disable_action_already_disabled_is_no_op(self):
        self.integration.is_enabled = False
        self.integration.save()
        response = self.client.post(self._url(), data = { 'action': 'disable' })
        self.assertEqual(response.status_code, 200)
        self.integration.refresh_from_db()
        self.assertFalse(self.integration.is_enabled)

    def test_disable_action_skips_credential_validation(self):
        # Disable bypasses the access probe — operators must be able
        # to disable a misconfigured integration without first
        # fixing the credentials.
        from unittest.mock import patch
        with patch(
                'hi.services.paperless.integration.PaperlessGateway.validate_access',
        ) as mock_probe:
            response = self.client.post(self._url(), data = { 'action': 'disable' })
        self.assertEqual(response.status_code, 200)
        mock_probe.assert_not_called()
        self.integration.refresh_from_db()
        self.assertFalse(self.integration.is_enabled)
