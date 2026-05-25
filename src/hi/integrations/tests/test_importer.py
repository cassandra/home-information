"""
Unit tests for the IntegrationImporter protocol scaffolding (Phase 2 of #358).
"""

import logging

from django.test import SimpleTestCase

from hi.integrations.importer.integration_importer import IntegrationImporter
from hi.integrations.importer.transient_models import (
    CandidateItem,
    IntegrationDiscardResult,
    IntegrationImportResult,
)

logging.disable(logging.CRITICAL)


class ImporterBaseClassTests(SimpleTestCase):

    def test_protocol_methods_raise_not_implemented(self):
        importer = IntegrationImporter()
        with self.assertRaises(NotImplementedError):
            importer.get_metadata()
        with self.assertRaises(NotImplementedError):
            importer.validate_configuration([])
        with self.assertRaises(NotImplementedError):
            importer.get_candidate_items()
        with self.assertRaises(NotImplementedError):
            importer.run_import()
        with self.assertRaises(NotImplementedError):
            importer.discard_imported_data('test')


class ImportTransientModelsTests(SimpleTestCase):

    def test_candidate_item(self):
        item = CandidateItem(name='Item One', integration_name='item-1')
        self.assertEqual(item.name, 'Item One')
        self.assertEqual(item.integration_name, 'item-1')

    def test_discard_result_defaults(self):
        result = IntegrationDiscardResult()
        self.assertEqual(result.count, 0)
        self.assertEqual(result.errors, [])

    def test_import_result_has_imports_property(self):
        empty = IntegrationImportResult(title='Empty')
        self.assertFalse(empty.has_imports)
        with_imports = IntegrationImportResult(
            title='With Imports',
            items_imported_count=3,
        )
        self.assertTrue(with_imports.has_imports)


class IntegrationGatewayImporterDefaultTests(SimpleTestCase):

    def test_default_returns_none(self):
        from hi.integrations.integration_gateway import IntegrationGateway
        gateway = IntegrationGateway()
        self.assertIsNone(gateway.get_importer())
