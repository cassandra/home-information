import logging
from unittest.mock import Mock, patch

from django.test import TestCase
from requests import HTTPError

from hi.integrations.exceptions import IntegrationAttributeError

from hi.apps.attribute.thumbnail import ThumbnailHelpers
from hi.services.immich.im_referencer import ImmichExternalReferencer


logging.disable(logging.CRITICAL)


def _envelope(*assets):
    return {
        'assets': {
            'items': list(assets),
            'total': len(assets),
            'count': len(assets),
            'nextPage': None,
        },
        'albums': {'items': [], 'total': 0, 'count': 0, 'nextPage': None},
    }


def _asset(asset_id='abc', **kwargs):
    a = {
        'id': asset_id,
        'originalFileName': f'{asset_id}.jpg',
        'originalMimeType': 'image/jpeg',
        'type': 'IMAGE',
        'fileCreatedAt': '2025-08-14T10:32:00.000Z',
        'exifInfo': {'city': 'Portland', 'country': 'USA'},
    }
    a.update(kwargs)
    return a


def _make_client(envelope):
    client = Mock()
    client.search_smart.return_value = envelope
    client.build_asset_web_url.side_effect = (
        lambda asset_id: f'https://im.example.com/photos/{asset_id}'
    )
    return client


class TestSearchReferencesShortCircuits(TestCase):
    """Empty / whitespace queries must not provoke an upstream call."""

    @patch('hi.services.immich.im_referencer.build_client')
    def test_empty_query_returns_empty(self, mock_build):
        result = ImmichExternalReferencer().search_references(
            query = '', limit = 20,
        )
        self.assertEqual(result.results, [])
        self.assertIsNone(result.error_message)
        mock_build.assert_not_called()

    @patch('hi.services.immich.im_referencer.build_client')
    def test_whitespace_query_returns_empty(self, mock_build):
        result = ImmichExternalReferencer().search_references(
            query = '   ', limit = 20,
        )
        self.assertEqual(result.results, [])
        self.assertIsNone(result.error_message)
        mock_build.assert_not_called()


class TestSearchReferences(TestCase):

    @patch('hi.services.immich.im_referencer.build_client')
    def test_calls_smart_search_with_trimmed_query(self, mock_build):
        client = _make_client(_envelope(_asset('a1')))
        mock_build.return_value = client

        ImmichExternalReferencer().search_references(
            query = '  dishwasher  ', limit = 10,
        )

        client.search_smart.assert_called_once_with(
            query = 'dishwasher', size = 10,
        )

    @patch('hi.services.immich.im_referencer.build_client')
    def test_translates_assets_to_results(self, mock_build):
        client = _make_client(_envelope(
            _asset('a1', originalFileName = 'fridge.jpg'),
            _asset('a2', originalFileName = 'dishwasher.png',
                   originalMimeType = 'image/png'),
        ))
        mock_build.return_value = client

        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )

        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.results), 2)
        self.assertEqual(result.results[0].title, 'fridge.jpg')
        self.assertEqual(
            result.results[0].source_url,
            'https://im.example.com/photos/a1',
        )
        # Thumbnail is the HI proxy URL, NOT the upstream — browser
        # fetches via HI's session, HI fetches upstream with the
        # configured key.
        self.assertIn('/integration/services/immich/assets/a1/thumb/',
                      result.results[0].thumbnail_url)
        self.assertEqual(result.results[0].mime_type, 'image/jpeg')
        self.assertEqual(result.results[1].mime_type, 'image/png')

    @patch('hi.services.immich.im_referencer.build_client')
    def test_title_falls_back_to_id_when_filename_missing(self, mock_build):
        client = _make_client(_envelope(
            _asset('a1', originalFileName = None),
        ))
        mock_build.return_value = client

        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertEqual(result.results[0].title, 'a1')

    @patch('hi.services.immich.im_referencer.build_client')
    def test_limit_passes_through_as_size(self, mock_build):
        client = _make_client(_envelope())
        mock_build.return_value = client

        ImmichExternalReferencer().search_references(query = 'q', limit = 50)
        client.search_smart.assert_called_once_with(query = 'q', size = 50)

    @patch('hi.services.immich.im_referencer.build_client')
    def test_missing_assets_key_yields_empty(self, mock_build):
        # Defensive: don't blow up if upstream's envelope omits the
        # assets wrapper.
        client = _make_client({'albums': {}})
        mock_build.return_value = client
        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertEqual(result.results, [])
        self.assertIsNone(result.error_message)

    @patch('hi.services.immich.im_referencer.build_client')
    def test_missing_items_inside_assets_yields_empty(self, mock_build):
        client = _make_client({'assets': {}, 'albums': {}})
        mock_build.return_value = client
        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertEqual(result.results, [])
        self.assertIsNone(result.error_message)


class TestSearchReferencesErrorMessages(TestCase):
    """Failure paths must surface ``error_message`` (not raise) so
    the picker can render a distinct banner instead of falling back
    to "no results."""

    @patch('hi.services.immich.im_referencer.build_client',
           side_effect = IntegrationAttributeError('not configured'))
    def test_unconfigured_integration(self, _mock_build):
        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertEqual(result.results, [])
        self.assertIn('not configured', result.error_message)

    @patch('hi.services.immich.im_referencer.build_client',
           side_effect = RuntimeError('boom in build'))
    def test_unexpected_client_build_error(self, _mock_build):
        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertEqual(result.results, [])
        self.assertIn('Immich integration error', result.error_message)

    @patch('hi.services.immich.im_referencer.build_client')
    def test_http_401_names_unrecognized_key(self, mock_build):
        client = _make_client(_envelope())
        response = Mock()
        response.status_code = 401
        client.search_smart.side_effect = HTTPError('401', response = response)
        mock_build.return_value = client
        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertEqual(result.results, [])
        self.assertIn('not recognized', result.error_message)

    @patch('hi.services.immich.im_referencer.build_client')
    def test_http_403_names_asset_read_scope(self, mock_build):
        client = _make_client(_envelope())
        response = Mock()
        response.status_code = 403
        client.search_smart.side_effect = HTTPError('403', response = response)
        mock_build.return_value = client
        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertIn('asset.read', result.error_message)

    @patch('hi.services.immich.im_referencer.build_client')
    def test_http_500_surfaces_status_code(self, mock_build):
        client = _make_client(_envelope())
        response = Mock()
        response.status_code = 500
        client.search_smart.side_effect = HTTPError('500', response = response)
        mock_build.return_value = client
        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertIn('500', result.error_message)

    @patch('hi.services.immich.im_referencer.build_client')
    def test_unexpected_search_exception(self, mock_build):
        client = _make_client(_envelope())
        client.search_smart.side_effect = RuntimeError('boom')
        mock_build.return_value = client
        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertEqual(result.results, [])
        self.assertIn('Immich search failed', result.error_message)

    @patch('hi.services.immich.im_referencer.build_client')
    def test_translation_failure_surfaces_unexpected_response(self, mock_build):
        # A non-dict item in the assets list makes _translate's
        # ``asset.get(...)`` raise AttributeError. The referencer
        # must report it as an Immich-named error instead of letting
        # the exception escape to the framework's generic fallback.
        client = _make_client(_envelope('not-a-dict'))
        mock_build.return_value = client
        result = ImmichExternalReferencer().search_references(
            query = 'q', limit = 20,
        )
        self.assertEqual(result.results, [])
        self.assertIn('Immich', result.error_message)
        self.assertIn('unexpected', result.error_message.lower())


class TestBuildSecondaryText(TestCase):
    """The snippet replacement for photos. Returns None when nothing
    useful — template omits the snippet row in that case."""

    def test_returns_none_when_no_date_no_exif(self):
        self.assertIsNone(
            ImmichExternalReferencer._build_secondary_text({})
        )

    def test_date_only(self):
        result = ImmichExternalReferencer._build_secondary_text({
            'fileCreatedAt': '2025-08-14T10:32:00.000Z',
        })
        self.assertEqual(result, '2025-08-14')

    def test_city_and_country(self):
        result = ImmichExternalReferencer._build_secondary_text({
            'exifInfo': {'city': 'Portland', 'country': 'USA'},
        })
        self.assertEqual(result, 'Portland, USA')

    def test_city_only(self):
        result = ImmichExternalReferencer._build_secondary_text({
            'exifInfo': {'city': 'Portland'},
        })
        self.assertEqual(result, 'Portland')

    def test_country_only(self):
        result = ImmichExternalReferencer._build_secondary_text({
            'exifInfo': {'country': 'USA'},
        })
        self.assertEqual(result, 'USA')

    def test_date_and_place(self):
        result = ImmichExternalReferencer._build_secondary_text({
            'fileCreatedAt': '2025-08-14T10:32:00.000Z',
            'exifInfo': {'city': 'Portland', 'country': 'USA'},
        })
        self.assertEqual(result, '2025-08-14 · Portland, USA')

    def test_null_exif_treated_as_empty(self):
        result = ImmichExternalReferencer._build_secondary_text({
            'fileCreatedAt': '2025-08-14T10:32:00.000Z',
            'exifInfo': None,
        })
        self.assertEqual(result, '2025-08-14')


class TestAttachReferences(TestCase):
    """Cover each branch of the defensive thumbnail chain:
      1. upstream thumbnail succeeds
      2. upstream thumbnail fails → original succeeds → generate succeeds
      3. upstream thumbnail fails → original succeeds → generate fails
      4. upstream thumbnail fails → original fails
      5. video mime type → skip original fetch entirely
    Plus client-build failure aborts the batch silently.
    """

    def setUp(self):
        from hi.apps.entity.enums import EntityType
        from hi.apps.entity.models import Entity
        self.entity = Entity.objects.create(
            name='Fridge', entity_type_str=str(EntityType.APPLIANCE),
        )
        self.referencer = ImmichExternalReferencer()

    def tearDown(self):
        from hi.integrations.models import EntityExternalReference
        for row in EntityExternalReference.objects.filter(entity=self.entity):
            row.delete()

    def _selection(self, asset_id='uuid-1', title='Fridge plate',
                   source_url='https://im.example.com/photos/uuid-1',
                   mime_type='image/jpeg'):
        from hi.integrations.referencer.transient_models import (
            ExternalReferenceResult,
        )
        from hi.integrations.transient_models import IntegrationKey
        from hi.services.immich.im_metadata import ImmichMetaData
        return ExternalReferenceResult(
            integration_key=IntegrationKey(
                integration_id=ImmichMetaData.integration_id,
                integration_name=asset_id,
            ),
            title=title,
            source_url=source_url,
            mime_type=mime_type,
        )

    @patch.object(ImmichExternalReferencer, 'build_client')
    def test_upstream_thumbnail_success_attaches_with_upstream_bytes(
            self, mock_build):
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.return_value = {
            'content': b'UPSTREAM-PNG', 'mime_type': 'image/png',
        }
        mock_build.return_value = client

        self.referencer.attach_references(self.entity, [self._selection()])

        row = EntityExternalReference.objects.get(
            entity=self.entity, integration_name='uuid-1',
        )
        self.assertTrue(row.thumbnail.name)
        # Original fetch shouldn't have been attempted — upstream
        # thumbnail succeeded.
        client.download_original.assert_not_called()

    @patch.object(ThumbnailHelpers, 'bytes_to_thumbnail_png',
                  return_value=b'GENERATED-PNG')
    @patch.object(ImmichExternalReferencer, 'build_client')
    def test_thumbnail_fail_original_succeed_generate_succeed(
            self, mock_build, mock_generate):
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.side_effect = HTTPError('500')
        client.download_original.return_value = {
            'content': b'JPEG-RAW', 'mime_type': 'image/jpeg',
        }
        mock_build.return_value = client

        self.referencer.attach_references(self.entity, [self._selection()])

        row = EntityExternalReference.objects.get(
            entity=self.entity, integration_name='uuid-1',
        )
        self.assertTrue(row.thumbnail.name)
        mock_generate.assert_called_once_with(b'JPEG-RAW', 'image/jpeg')

    @patch.object(ThumbnailHelpers, 'bytes_to_thumbnail_png',
                  return_value=None)
    @patch.object(ImmichExternalReferencer, 'build_client')
    def test_thumbnail_fail_original_succeed_generate_fail(
            self, mock_build, _mock_generate):
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.side_effect = HTTPError('500')
        client.download_original.return_value = {
            'content': b'JPEG-RAW', 'mime_type': 'image/jpeg',
        }
        mock_build.return_value = client

        self.referencer.attach_references(self.entity, [self._selection()])

        row = EntityExternalReference.objects.get(
            entity=self.entity, integration_name='uuid-1',
        )
        self.assertFalse(row.thumbnail)

    @patch.object(ImmichExternalReferencer, 'build_client')
    def test_thumbnail_fail_original_fail_attaches_without_thumbnail(
            self, mock_build):
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.side_effect = HTTPError('500')
        client.download_original.side_effect = HTTPError('502')
        mock_build.return_value = client

        self.referencer.attach_references(self.entity, [self._selection()])

        row = EntityExternalReference.objects.get(
            entity=self.entity, integration_name='uuid-1',
        )
        self.assertFalse(row.thumbnail)

    @patch.object(ImmichExternalReferencer, 'build_client')
    def test_video_mime_type_skips_original_fetch(self, mock_build):
        # Downloading an entire video just to discover the generator
        # can't make a poster is wasteful. The chain should skip
        # original-fetch for non-image mime types.
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.side_effect = HTTPError('500')
        mock_build.return_value = client

        self.referencer.attach_references(
            self.entity,
            [self._selection(mime_type='video/mp4')],
        )

        row = EntityExternalReference.objects.get(
            entity=self.entity, integration_name='uuid-1',
        )
        self.assertFalse(row.thumbnail)
        client.download_original.assert_not_called()

    @patch.object(ImmichExternalReferencer, 'build_client',
                  side_effect=IntegrationAttributeError('not configured'))
    def test_client_build_failure_aborts_silently(self, _mock_build):
        from hi.integrations.models import EntityExternalReference
        self.referencer.attach_references(self.entity, [self._selection()])
        self.assertEqual(
            EntityExternalReference.objects.filter(entity=self.entity).count(),
            0,
        )
