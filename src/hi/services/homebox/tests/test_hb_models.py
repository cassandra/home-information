import logging
from django.test import SimpleTestCase

from hi.services.homebox.hb_models import HbItem


logging.disable(logging.CRITICAL)


class TestHbItem(SimpleTestCase):

    def _create_item(self, **kwargs):
        base_data = {
            'id': 'item-1',
            'name': 'Drill',
            'description': 'Cordless drill',
            'quantity': 2,
            'insured': True,
            'archived': False,
            'createdAt': '2025-01-01T00:00:00Z',
            'updatedAt': '2025-01-02T00:00:00Z',
            'purchasePrice': 99.5,
            'assetId': 'A-1',
            'syncChildItemsLocations': True,
            'serialNumber': 'S-1',
            'modelNumber': 'M-1',
            'manufacturer': 'ACME',
            'lifetimeWarranty': False,
            'warrantyExpires': '2026-01-01',
            'warrantyDetails': '2 years',
            'purchaseTime': '2025-01-01',
            'purchaseFrom': 'Store',
            'soldTime': '2025-02-01',
            'soldTo': 'Buyer',
            'soldPrice': 80,
            'soldNotes': 'Used',
            'notes': 'Shelf A',
            'location': {'id': 'loc-1'},
            'labels': [{'id': 'lab-1'}],
            'attachments': [{'id': 'att-1'}],
            'fields': [{'id': 'f-1'}],
        }
        base_data.update(kwargs)
        return HbItem(api_dict=base_data)

    def test_returns_expected_values_for_valid_types(self):
        item = self._create_item()

        self.assertEqual(item.id, 'item-1')
        self.assertEqual(item.name, 'Drill')
        self.assertEqual(item.description, 'Cordless drill')
        self.assertEqual(item.quantity, 2)
        self.assertTrue(item.insured)
        self.assertFalse(item.archived)
        self.assertEqual(item.created_at, '2025-01-01T00:00:00Z')
        self.assertEqual(item.updated_at, '2025-01-02T00:00:00Z')
        self.assertEqual(item.purchase_price, 99.5)
        self.assertEqual(item.asset_id, 'A-1')
        self.assertTrue(item.sync_child_items_locations)
        self.assertEqual(item.serial_number, 'S-1')
        self.assertEqual(item.model_number, 'M-1')
        self.assertEqual(item.manufacturer, 'ACME')
        self.assertFalse(item.lifetime_warranty)
        self.assertEqual(item.warranty_expires, '2026-01-01')
        self.assertEqual(item.warranty_details, '2 years')
        self.assertEqual(item.purchase_time, '2025-01-01')
        self.assertEqual(item.purchase_from, 'Store')
        self.assertEqual(item.sold_time, '2025-02-01')
        self.assertEqual(item.sold_to, 'Buyer')
        self.assertEqual(item.sold_price, 80)
        self.assertEqual(item.sold_notes, 'Used')
        self.assertEqual(item.notes, 'Shelf A')
        self.assertEqual(item.location, {'id': 'loc-1'})
        self.assertEqual(item.labels, [{'id': 'lab-1'}])
        self.assertEqual(item.attachments, [{'id': 'att-1'}])
        self.assertEqual(item.fields, [{'id': 'f-1'}])

    def test_returns_none_for_invalid_typed_optional_fields(self):
        item = self._create_item(
            quantity='2',
            insured='true',
            archived='false',
            createdAt='   ',
            updatedAt=123,
            purchasePrice='99.5',
            assetId='   ',
            syncChildItemsLocations='yes',
            lifetimeWarranty='false',
            warrantyExpires='   ',
            purchaseTime=0,
            soldTime='',
            soldPrice='80',
            location='garage',
            labels='tools',
        )

        self.assertIsNone(item.quantity)
        self.assertIsNone(item.insured)
        self.assertIsNone(item.archived)
        self.assertIsNone(item.created_at)
        self.assertIsNone(item.updated_at)
        self.assertIsNone(item.purchase_price)
        self.assertIsNone(item.asset_id)
        self.assertIsNone(item.sync_child_items_locations)
        self.assertIsNone(item.lifetime_warranty)
        self.assertIsNone(item.warranty_expires)
        self.assertIsNone(item.purchase_time)
        self.assertIsNone(item.sold_time)
        self.assertIsNone(item.sold_price)
        self.assertIsNone(item.location)
        self.assertIsNone(item.labels)

    def test_returns_empty_collections_or_strings_when_missing(self):
        item = HbItem(api_dict={'id': 'item-2'})

        self.assertEqual(item.name, '')
        self.assertEqual(item.description, '')
        self.assertEqual(item.serial_number, '')
        self.assertEqual(item.model_number, '')
        self.assertEqual(item.manufacturer, '')
        self.assertEqual(item.warranty_details, '')
        self.assertEqual(item.purchase_from, '')
        self.assertEqual(item.sold_to, '')
        self.assertEqual(item.sold_notes, '')
        self.assertEqual(item.notes, '')
        self.assertEqual(item.attachments, [])
        self.assertEqual(item.fields, [])
