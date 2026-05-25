"""Tests for the IntegrationGateway base-class default behavior
around the external-view-data hook plus basic shape checks on the
ExternalViewData dataclass hierarchy.

The gateway hook defaults to None so integrations without an
external-view override automatically suppress the entity-detail
modal's external-data view region. Pinning this default catches
accidental override drift on the base class.
"""
import logging

from django.test import TestCase

from hi.integrations.connector.external_view_data import (
    AttachmentRef,
    CustomTemplateViewData,
    MinimalViewData,
    NameValuePair,
    StructuredViewData,
)
from hi.integrations.connector.integration_connector import IntegrationConnector

logging.disable(logging.CRITICAL)


class IntegrationConnectorExternalViewDataDefaultTests(TestCase):

    def test_get_external_view_data_defaults_to_none(self):
        connector = IntegrationConnector()
        self.assertIsNone(connector.get_external_view_data(entity=None))


class ExternalViewDataDefaultTemplateNameTests(TestCase):
    """Each subclass has a load-bearing default template_name that
    drives the external-data view include. Direct assertions guard
    against silent renames of the framework partials."""

    def test_structured_view_data_default_template_name(self):
        instance = StructuredViewData(
            attributes=[NameValuePair(name='k', value='v')],
        )
        self.assertEqual(
            instance.template_name,
            'integrations/external_data/entity/structured.html',
        )

    def test_minimal_view_data_default_template_name(self):
        instance = MinimalViewData(deep_link_url='https://example/')
        self.assertEqual(
            instance.template_name,
            'integrations/external_data/entity/minimal.html',
        )

    def test_custom_template_view_data_takes_explicit_template_name(self):
        instance = CustomTemplateViewData(
            template_name='services/foo/templates/foo/custom.html',
            context={'k': 'v'},
        )
        self.assertEqual(
            instance.template_name,
            'services/foo/templates/foo/custom.html',
        )

    def test_structured_view_data_carries_attachments_independently(self):
        instance = StructuredViewData(
            attachments=[
                AttachmentRef(id='a', title='A', mime_type='image/png'),
            ],
        )
        self.assertEqual(len(instance.attachments), 1)
        self.assertEqual(instance.attributes, [])

    def test_custom_template_view_data_requires_template_name(self):
        """CustomTemplateViewData has no usable default template_name —
        the empty default would silently misroute the include. Empty
        and whitespace-only values must fail loudly at construction."""
        with self.assertRaises(ValueError):
            CustomTemplateViewData()
        with self.assertRaises(ValueError):
            CustomTemplateViewData(template_name='')
        with self.assertRaises(ValueError):
            CustomTemplateViewData(template_name='   ')
