import logging
from unittest.mock import Mock

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.services.homebox.hb_converter import HbConverter
from hi.services.homebox.hb_models import HbItem


logging.disable(logging.CRITICAL)


class TestHbConverter(TestCase):

    def _mock_item(self, item_id='item-1', name='Item 1', description='desc', quantity=1):
        api_dict = {
            'id': item_id,
            'name': name,
            'description': description,
            'quantity': quantity,
            'location': {'id': 'loc-1', 'name': 'Garage'},
            'tags': [{'id': 'lab-1', 'name': 'Tools'}],
            'fields': [],
            'attachments': [],
        }

        client = Mock()
        client.download_attachment.return_value = None

        return HbItem(api_dict=api_dict, client=client)

    def test_hb_item_to_attribute_field_list_contains_top_level_fields(self):
        item = self._mock_item(item_id='item-top-level')
        item.api_dict['description'] = 'Portable drill'
        item.api_dict['serialNumber'] = 'SN-123'
        item.api_dict['modelNumber'] = 'MD-456'
        item.api_dict['manufacturer'] = 'ACME'
        item.api_dict['assetId'] = 'AS-789'
        item.api_dict['purchaseFrom'] = 'Big Box Store'
        item.api_dict['purchaseTime'] = '2024-01-15'
        item.api_dict['warrantyDetails'] = '2 year limited'
        item.api_dict['warrantyExpires'] = '2026-01-15'
        item.api_dict['notes'] = 'Keep in workshop'

        hb_field_list = HbConverter.hb_item_to_attribute_field_list( hb_item = item )
        field_id_to_field = { field.get( 'id' ): field for field in hb_field_list }

        self.assertEqual( field_id_to_field['hb_item:description']['textValue'], 'Portable drill' )
        self.assertEqual( field_id_to_field['hb_item:serial_number']['textValue'], 'SN-123' )
        self.assertEqual( field_id_to_field['hb_item:model_number']['textValue'], 'MD-456' )
        self.assertEqual( field_id_to_field['hb_item:manufacturer']['textValue'], 'ACME' )
        self.assertEqual( field_id_to_field['hb_item:asset_id']['textValue'], 'AS-789' )
        self.assertEqual( field_id_to_field['hb_item:purchase_from']['textValue'], 'Big Box Store' )
        self.assertEqual( field_id_to_field['hb_item:purchase_time']['textValue'], '2024-01-15' )
        self.assertEqual( field_id_to_field['hb_item:warranty_details']['textValue'], '2 year limited' )
        self.assertEqual( field_id_to_field['hb_item:warranty_expires']['textValue'], '2026-01-15' )
        self.assertEqual( field_id_to_field['hb_item:notes']['textValue'], 'Keep in workshop' )

    def test_hb_item_attachment_maps_to_file_attribute_payload(self):
        item = self._mock_item(item_id='item-with-attachment')
        item.api_dict['attachments'] = [{
            'id': 'att-1',
            'title': 'Manual',
            'mimeType': 'text/plain',
            'path': 'some/path',
        }]
        item.client.download_attachment.return_value = {
            'content': b'attachment-content',
            'mime_type': 'text/plain',
            'filename': 'Manual.txt',
            'source_url': 'https://example/download',
        }

        attachment_field_list = HbConverter.hb_item_to_attachment_field_list(hb_item=item)
        attachment_data = attachment_field_list[0]
        payload = HbConverter.hb_attachment_to_attribute_payload(hb_attachment=attachment_data, order_id=0)

        self.assertEqual(payload['value_type_str'], str(AttributeValueType.FILE))
        self.assertEqual(payload['name'], 'Manual')
        self.assertEqual(payload['file_mime_type'], 'text/plain')
        self.assertIn('file_value', payload)


class TestHbConverterPayloadTimestampOmission(TestCase):
    """Regression coverage for the timestamp-omission contract on
    ``hb_item_to_entity_payload``.

    Timestamps are deliberately excluded from the payload — they
    are metadata about *when* a change happened, not *what*
    changed. Including them caused spurious 'updated' reports on
    every refresh because real HomeBox can tick ``updatedAt`` for
    housekeeping events the operator doesn't care about. These
    tests pin the contract so a future re-add (e.g., 'for
    completeness') silently re-introducing the bug fails loudly."""

    def _mock_item(self, **api_overrides):
        api_dict = {
            'id': 'item-1',
            'name': 'Item 1',
            'description': 'desc',
            'quantity': 1,
            'createdAt': '2026-01-01T00:00:00+00:00',
            'updatedAt': '2026-01-01T00:00:00+00:00',
            'location': {'id': 'loc-1', 'name': 'Garage'},
            'tags': [{'id': 'lab-1', 'name': 'Tools'}],
            'fields': [],
            'attachments': [],
        }
        api_dict.update(api_overrides)
        return HbItem(api_dict=api_dict, client=Mock())

    def test_payload_excludes_timestamp_keys(self):
        item = self._mock_item()
        payload = HbConverter.hb_item_to_entity_payload(hb_item=item)
        self.assertNotIn('created_at', payload)
        self.assertNotIn('updated_at', payload)

    def test_payloads_compare_equal_when_only_timestamps_differ(self):
        """The change-detection signal: two payloads identical
        except for timestamps must compare equal so a refresh
        against unchanged upstream content reports zero updates."""
        earlier = self._mock_item(
            createdAt='2026-01-01T00:00:00+00:00',
            updatedAt='2026-01-01T00:00:00+00:00',
        )
        later = self._mock_item(
            createdAt='2026-04-15T12:34:56+00:00',
            updatedAt='2026-05-04T08:00:00+00:00',
        )
        self.assertEqual(
            HbConverter.hb_item_to_entity_payload(hb_item=earlier),
            HbConverter.hb_item_to_entity_payload(hb_item=later),
        )


class TestHbItemToEntityPayloadGroupingFields(TestCase):
    """Pin the flat shape of the location/tags grouping fields.

    These fields feed placement grouping (issue #364). Storing
    them flat — string for location, list of strings for tags —
    keeps payload-diff comparisons stable and avoids leaking HB
    metadata (color, timestamps) that no downstream code reads.
    Live HB API responses remain the source of truth for the rich
    structures."""

    def _mock_item(self, **api_overrides):
        api_dict = {
            'id': 'item-1',
            'name': 'Item 1',
            'description': 'desc',
            'quantity': 1,
            'location': {'id': 'loc-1', 'name': 'Garage'},
            'tags': [
                {'id': 'lab-1', 'name': 'Tools'},
                {'id': 'lab-2', 'name': 'Power'},
            ],
            'fields': [],
            'attachments': [],
        }
        api_dict.update(api_overrides)
        return HbItem(api_dict=api_dict, client=Mock())

    def test_location_persists_as_flat_name_string(self):
        payload = HbConverter.hb_item_to_entity_payload(hb_item=self._mock_item())
        self.assertEqual(payload['location'], 'Garage')

    def test_tags_persist_as_flat_name_list(self):
        payload = HbConverter.hb_item_to_entity_payload(hb_item=self._mock_item())
        self.assertEqual(payload['tags'], ['Tools', 'Power'])

    def test_missing_location_yields_none(self):
        payload = HbConverter.hb_item_to_entity_payload(hb_item=self._mock_item(location=None))
        self.assertIsNone(payload['location'])

    def test_missing_tags_yields_empty_list(self):
        payload = HbConverter.hb_item_to_entity_payload(hb_item=self._mock_item(tags=None))
        self.assertEqual(payload['tags'], [])

    def test_tags_without_name_are_skipped(self):
        item = self._mock_item(tags=[
            {'id': 'lab-1', 'name': 'Tools'},
            {'id': 'lab-2'},
            {'id': 'lab-3', 'name': ''},
            {'id': 'lab-4', 'name': 'Power'},
        ])
        payload = HbConverter.hb_item_to_entity_payload(hb_item=item)
        self.assertEqual(payload['tags'], ['Tools', 'Power'])


class TestHbItemToEntityType(TestCase):
    """Heuristic EntityType assignment from HomeBox item text fields.

    Verifies the two-pass priority — outer field priority (name then
    description) and inner keyword specificity (longer / multi-word
    keywords win) — and that word-boundary semantics prevent false
    positives like ``drilling`` matching ``drill``."""

    def _item(self, name='', description=''):
        from unittest.mock import Mock
        api_dict = {
            'id': 'test-item',
            'name': name,
            'description': description,
            'location': {'id': 'loc-1', 'name': 'Garage'},
            'tags': [],
            'fields': [],
            'attachments': [],
        }
        client = Mock()
        return HbItem(api_dict=api_dict, client=client)

    # --- positive matches across categories -----------------------

    def test_tool_match_in_name(self):
        from hi.apps.entity.enums import EntityType
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(name='Cordless Drill')),
            EntityType.TOOL,
        )

    def test_light_match_in_name(self):
        from hi.apps.entity.enums import EntityType
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(name='Floor Lamp')),
            EntityType.LIGHT,
        )

    def test_camera_match_in_name(self):
        from hi.apps.entity.enums import EntityType
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(name='Front Door Camera')),
            EntityType.CAMERA,
        )

    def test_refrigerator_match_in_name(self):
        from hi.apps.entity.enums import EntityType
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(name='Kitchen Refrigerator')),
            EntityType.REFRIGERATOR,
        )

    def test_router_match_in_name(self):
        from hi.apps.entity.enums import EntityType
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(name='Wi-Fi Router')),
            EntityType.NETWORK_SWITCH,
        )

    # --- multi-word beats single-word within the same field ------

    def test_multi_word_beats_single_word_in_same_field(self):
        # Item named 'Ceiling Fan' should match the multi-word
        # 'ceiling fan' keyword (CEILING_FAN), not just 'fan'
        # — even if 'fan' were also in the keyword map.
        from hi.apps.entity.enums import EntityType
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(name='Ceiling Fan')),
            EntityType.CEILING_FAN,
        )

    def test_leaf_blower_beats_bare_blower(self):
        from hi.apps.entity.enums import EntityType
        # The bare 'blower' keyword would also match, but the multi-
        # word 'leaf blower' is sorted first by specificity and wins.
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(name='Leaf Blower')),
            EntityType.LEAF_BLOWER,
        )

    # --- field priority: name beats description ------------------

    def test_name_match_beats_description_match(self):
        from hi.apps.entity.enums import EntityType
        # Name says drill (TOOL); description mentions lamp (LIGHT).
        # Name wins.
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(
                name='Cordless Drill',
                description='Used as accessory next to the lamp',
            )),
            EntityType.TOOL,
        )

    def test_description_used_when_name_has_no_match(self):
        from hi.apps.entity.enums import EntityType
        # Name carries no category signal (just brand/model); the
        # description identifies it as a leaf blower.
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(
                name='Acme BG-2200',
                description='Cordless leaf blower with two batteries',
            )),
            EntityType.LEAF_BLOWER,
        )

    # --- word-boundary correctness -------------------------------

    def test_drilling_does_not_match_drill(self):
        from hi.apps.entity.enums import EntityType
        # 'drilling' is not the same as 'drill' — boundary regex
        # must reject the suffix match.
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(
                name='Drilling Machine',
            )),
            EntityType.OTHER,
        )

    def test_case_insensitive(self):
        from hi.apps.entity.enums import EntityType
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(name='DRILL')),
            EntityType.TOOL,
        )

    # --- edge cases ----------------------------------------------

    def test_no_match_returns_other(self):
        from hi.apps.entity.enums import EntityType
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(
                name='Mystery Object',
                description='Unknown thing',
            )),
            EntityType.OTHER,
        )

    def test_empty_name_and_description_returns_other(self):
        from hi.apps.entity.enums import EntityType
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(name='', description='')),
            EntityType.OTHER,
        )

    def test_only_description_present(self):
        from hi.apps.entity.enums import EntityType
        # No name field at all (None-like) — description still
        # contributes.
        self.assertEqual(
            HbConverter.hb_item_to_entity_type(hb_item=self._item(
                name='',
                description='Mountain bike camera mount',
            )),
            EntityType.CAMERA,
        )
