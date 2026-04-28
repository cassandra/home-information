"""
Tests for IntegrationViewMixin.validate_attributes_extra_helper, the
two-stage save-time validation entry point.

Stage 1: gateway.validate_configuration (schema-only, fast, offline)
Stage 2: gateway.test_connection      (live probe, bounded timeout)

Both stages must surface their failure inline as a non-form error so the
user sees the cause without a silent save followed by a delayed background
error.
"""

import logging
from unittest.mock import Mock

from django.test import SimpleTestCase

from hi.apps.system.enums import HealthStatusType
from hi.integrations.integration_manager import IntegrationManager
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationValidationResult,
)
from hi.integrations.view_mixins import IntegrationViewMixin

logging.disable(logging.CRITICAL)


def _build_formset(form_data_list):
    """
    Build a fake formset that the helper can iterate. Each entry in
    form_data_list maps to a single 'form' with cleaned_data.
    """
    formset = Mock()
    formset._non_form_errors = []
    forms = []
    for cleaned_data in form_data_list:
        form = Mock()
        form.cleaned_data = cleaned_data
        form.instance = Mock()
        form.instance.value = ''
        forms.append(form)
    formset.__iter__ = lambda self: iter(forms)
    return formset


def _build_attr_item_context(gateway):
    integration_data = Mock()
    integration_data.integration_gateway = gateway
    attr_item_context = Mock()
    attr_item_context.integration_data = integration_data
    return attr_item_context


class ValidateAttributesExtraHelperTest(SimpleTestCase):

    def setUp(self):
        self.mixin = IntegrationViewMixin()

    def test_success_path_runs_both_stages(self):
        """Both stages succeed → no errors appended to the formset."""
        gateway = Mock()
        gateway.validate_configuration.return_value = (
            IntegrationValidationResult.success()
        )
        gateway.test_connection.return_value = ConnectionTestResult.success()

        formset = _build_formset([{'value': 'token'}])
        ctx = _build_attr_item_context(gateway)

        self.mixin.validate_attributes_extra_helper(
            attr_item_context=ctx,
            regular_attributes_formset=formset,
            error_title='Test',
        )

        self.assertEqual(formset._non_form_errors, [])
        gateway.validate_configuration.assert_called_once()
        gateway.test_connection.assert_called_once()
        kwargs = gateway.test_connection.call_args.kwargs
        self.assertEqual(kwargs['timeout_secs'],
                         IntegrationManager.HEALTH_CHECK_TIMEOUT_SECS)

    def test_schema_failure_short_circuits_before_connection_probe(self):
        """Stage 1 failure must skip Stage 2 entirely (no network)."""
        gateway = Mock()
        gateway.validate_configuration.return_value = (
            IntegrationValidationResult.error(
                status=HealthStatusType.ERROR,
                error_message='Missing API URL',
            )
        )

        formset = _build_formset([{'value': ''}])
        ctx = _build_attr_item_context(gateway)

        self.mixin.validate_attributes_extra_helper(
            attr_item_context=ctx,
            regular_attributes_formset=formset,
            error_title='Test',
        )

        gateway.test_connection.assert_not_called()
        self.assertEqual(len(formset._non_form_errors), 1)
        self.assertIn('Missing API URL', formset._non_form_errors[0])

    def test_connection_failure_after_schema_success_appends_error(self):
        """Stage 1 passes, Stage 2 fails → its message surfaces inline."""
        gateway = Mock()
        gateway.validate_configuration.return_value = (
            IntegrationValidationResult.success()
        )
        gateway.test_connection.return_value = ConnectionTestResult.failure(
            'Cannot connect to upstream'
        )

        formset = _build_formset([{'value': 'token'}])
        ctx = _build_attr_item_context(gateway)

        self.mixin.validate_attributes_extra_helper(
            attr_item_context=ctx,
            regular_attributes_formset=formset,
            error_title='Test',
        )

        gateway.test_connection.assert_called_once()
        self.assertEqual(len(formset._non_form_errors), 1)
        self.assertIn('Cannot connect to upstream', formset._non_form_errors[0])

    def test_unexpected_gateway_exception_propagates(self):
        """
        validate_configuration / test_connection are required by their
        contracts to convert internal exceptions into result objects
        (IntegrationValidationResult.error / ConnectionTestResult.failure).
        If a gateway impl is buggy and throws anyway, the helper does NOT
        coerce that exception into a form-level error — it lets the
        exception propagate so the bug surfaces through Django's error
        pipeline rather than being silently masked as a connection
        failure.
        """
        gateway = Mock()
        gateway.validate_configuration.side_effect = RuntimeError('boom')

        formset = _build_formset([{'value': 'token'}])
        ctx = _build_attr_item_context(gateway)

        with self.assertRaises(RuntimeError):
            self.mixin.validate_attributes_extra_helper(
                attr_item_context=ctx,
                regular_attributes_formset=formset,
                error_title='Test',
            )
