"""HomeBoxImporter contract + behavior tests."""
import logging
from unittest.mock import Mock, patch

from django.test import TestCase

from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity
from hi.integrations.importer.transient_models import IntegrationDiscardResult
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.importer.homebox_importer import HomeBoxImporter
from hi.services.homebox.hb_models import HbItem

logging.disable(logging.CRITICAL)


def _hb_item(item_id, name='Item', archived=False, location_name='Garage', tag_names=None):
    return HbItem(
        api_dict={
            'id': item_id,
            'name': name,
            'archived': archived,
            'location': {'id': 'loc-1', 'name': location_name} if location_name else None,
            'tags': [{'name': t} for t in (tag_names or [])],
            'fields': [],
            'attachments': [],
        },
        client=Mock(),
    )


class TestHomeBoxImporterGetCandidateItems(TestCase):

    def test_returns_unarchived_items(self):
        importer = HomeBoxImporter()
        mock_manager = Mock()
        mock_manager.hb_client = Mock()
        mock_manager.include_filter = ''
        mock_manager.exclude_filter = ''
        mock_manager.fetch_hb_items_summary_from_api.return_value = [
            {'id': 'item-1', 'name': 'Hammer', 'archived': False},
            {'id': 'item-2', 'name': 'Saw', 'archived': True},
            {'id': 'item-3', 'name': 'Screwdriver', 'archived': False},
        ]
        with patch.object(HomeBoxImporter, 'hb_manager', return_value=mock_manager):
            candidates = importer.get_candidate_items()

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            sorted(c.integration_name for c in candidates),
            ['item-1', 'item-3'],
        )

    def test_returns_empty_when_no_client(self):
        importer = HomeBoxImporter()
        mock_manager = Mock()
        mock_manager.hb_client = None
        with patch.object(HomeBoxImporter, 'hb_manager', return_value=mock_manager):
            self.assertEqual(importer.get_candidate_items(), [])


class TestHomeBoxImporterRunImport(TestCase):

    def test_skips_already_imported_items(self):
        # An existing imported entity blocks re-import of the same id.
        Entity.objects.create(
            previous_integration_id=HbMetaData.integration_id,
            previous_integration_name='item-1',
            name='Already imported',
            entity_type_str=str(EntityType.OTHER),
        )
        importer = HomeBoxImporter()
        mock_manager = Mock()
        mock_manager.hb_client = Mock()
        mock_manager.include_filter = ''
        mock_manager.exclude_filter = ''
        mock_manager.fetch_hb_items_from_api.return_value = [
            _hb_item('item-1', 'Should skip'),
            _hb_item('item-2', 'Should import'),
        ]
        with patch.object(HomeBoxImporter, 'hb_manager', return_value=mock_manager):
            result = importer.run_import()

        self.assertEqual(result.items_imported_count, 1)
        self.assertEqual(result.items_skipped_count, 1)
        self.assertEqual(result.error_list, [])
        new_entity = Entity.objects.get(previous_integration_name='item-2')
        self.assertTrue(new_entity.is_imported)
        self.assertTrue(new_entity.allow_internal_attributes)
        self.assertIsNone(new_entity.integration_id)
        self.assertEqual(new_entity.previous_integration_id, HbMetaData.integration_id)

    def test_per_item_failure_does_not_abort_batch(self):
        importer = HomeBoxImporter()
        mock_manager = Mock()
        mock_manager.hb_client = Mock()
        mock_manager.include_filter = ''
        mock_manager.exclude_filter = ''
        mock_manager.fetch_hb_items_from_api.return_value = [
            _hb_item('item-a', 'Item A'),
            _hb_item('item-b', 'Item B'),
        ]
        # First item raises during entity creation; second proceeds.
        with patch.object(HomeBoxImporter, 'hb_manager', return_value=mock_manager):
            with patch(
                'hi.services.homebox.importer.homebox_importer.HbEntityFactory.create_models_for_hb_item',
                side_effect=[RuntimeError('upstream blew up'), Mock(name='entity-b')],
            ):
                result = importer.run_import()

        self.assertEqual(result.items_imported_count, 1)
        self.assertEqual(len(result.error_list), 1)
        self.assertIn('item-a', result.error_list[0])


class TestHomeBoxImporterDiscard(TestCase):

    def test_discard_targets_only_imported(self):
        # Imported entity — should be removed.
        Entity.objects.create(
            previous_integration_id=HbMetaData.integration_id,
            previous_integration_name='import-1',
            name='Imported',
            entity_type_str=str(EntityType.OTHER),
            allow_internal_attributes=True,
        )
        # Connect-mode entity — must be left alone.
        Entity.objects.create(
            integration_id=HbMetaData.integration_id,
            integration_name='connect-1',
            name='Connected',
            entity_type_str=str(EntityType.OTHER),
            allow_internal_attributes=False,
        )

        importer = HomeBoxImporter()
        discard_result = importer.discard_imported_data(
            integration_id=HbMetaData.integration_id,
        )

        self.assertIsInstance(discard_result, IntegrationDiscardResult)
        self.assertEqual(discard_result.count, 1)
        self.assertFalse(
            Entity.objects.filter(previous_integration_name='import-1').exists()
        )
        self.assertTrue(
            Entity.objects.filter(integration_name='connect-1').exists()
        )

    def test_discard_with_no_imported_returns_zero(self):
        importer = HomeBoxImporter()
        result = importer.discard_imported_data(integration_id=HbMetaData.integration_id)
        self.assertEqual(result.count, 0)
        self.assertEqual(result.errors, [])


class TestHomeBoxImporterFilter(TestCase):
    """End-to-end coverage of the include/exclude filter on the
    importer paths — preview (candidate items) and the import
    itself."""

    def test_get_candidate_items_honors_include_filter(self):
        importer = HomeBoxImporter()
        mock_manager = Mock()
        mock_manager.hb_client = Mock()
        mock_manager.include_filter = 'Garage'
        mock_manager.exclude_filter = ''
        mock_manager.fetch_hb_items_summary_from_api.return_value = [
            {'id': '1', 'name': 'A', 'location': {'name': 'Garage'}, 'tags': []},
            {'id': '2', 'name': 'B', 'location': {'name': 'Basement'}, 'tags': []},
        ]
        with patch.object(HomeBoxImporter, 'hb_manager', return_value=mock_manager):
            candidates = importer.get_candidate_items()

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].integration_name, '1')

    def test_run_import_filters_and_populates_count(self):
        importer = HomeBoxImporter()
        mock_manager = Mock()
        mock_manager.hb_client = Mock()
        mock_manager.include_filter = 'Garage'
        mock_manager.exclude_filter = ''
        mock_manager.fetch_hb_items_from_api.return_value = [
            _hb_item('item-1', location_name='Garage'),
            _hb_item('item-2', location_name='Basement'),
            _hb_item('item-3', location_name='Garage'),
        ]
        with patch.object(HomeBoxImporter, 'hb_manager', return_value=mock_manager):
            result = importer.run_import()

        # 2 items in Garage imported; 1 in Basement filtered out.
        self.assertEqual(result.items_imported_count, 2)
        self.assertEqual(result.items_filtered_count, 1)
        self.assertTrue(any('Filtered 1 item(s)' in message
                            for message in result.info_list))
        self.assertIn('Include Items By Location/Tag', result.footer_message)
