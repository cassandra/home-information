"""Tests for the EXTERNAL_REFERENCE referencer.

Covers the two surfaces that matter for picker UX: snippet
extraction (window around the matched query, with paperless-style
fallbacks when no match) and the end-to-end translation of a
paperless documents-search response into ExternalReferenceResult
rows the framework can hand to the picker.
"""
import logging
from unittest.mock import Mock, patch

from django.test import TestCase
from requests import HTTPError

from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from hi.services.paperless.enums import PlAttributeType
from hi.services.paperless.pl_metadata import PaperlessMetaData
from hi.apps.attribute.thumbnail import ThumbnailHelpers
from hi.services.paperless.pl_referencer import PaperlessExternalReferencer


logging.disable(logging.CRITICAL)


def _make_attr(integration, attr_type, value):
    attr = IntegrationAttribute(
        integration = integration,
        name = attr_type.label,
        value = value,
        value_type_str = str(AttributeValueType.TEXT),
        attribute_type_str = 'PREDEFINED',
    )
    attr.integration_key = IntegrationKey(
        integration_id = PaperlessMetaData.integration_id,
        integration_name = str(attr_type),
    )
    attr.save()
    return attr


class TestSnippetExtraction(TestCase):

    def test_none_for_empty_content(self):
        # Empty content => omit the snippet row entirely in the
        # picker rather than render an empty placeholder.
        self.assertIsNone(
            PaperlessExternalReferencer._extract_snippet(
                content = '', query = 'q',
            )
        )

    def test_short_content_returned_verbatim(self):
        self.assertEqual(
            PaperlessExternalReferencer._extract_snippet(
                content = 'Short doc text.', query = 'missing',
            ),
            'Short doc text.',
        )

    def test_long_content_without_match_truncates(self):
        result = PaperlessExternalReferencer._extract_snippet(
            content = 'A' * 500, query = 'missing',
        )
        self.assertLessEqual(len(result), 161)  # 160 + the ellipsis
        self.assertTrue(result.endswith('…'))

    def test_match_in_middle_emits_leading_and_trailing_ellipses(self):
        content = 'x' * 200 + ' DISHWASHER ' + 'y' * 200
        result = PaperlessExternalReferencer._extract_snippet(
            content = content, query = 'dishwasher',
        )
        self.assertIn('DISHWASHER', result)
        self.assertTrue(result.startswith('…'))
        self.assertTrue(result.endswith('…'))

    def test_match_at_start_no_leading_ellipsis(self):
        result = PaperlessExternalReferencer._extract_snippet(
            content = 'Warranty info follows.', query = 'warranty',
        )
        self.assertFalse(result.startswith('…'))

    def test_case_insensitive_match(self):
        result = PaperlessExternalReferencer._extract_snippet(
            content = 'The DISHWASHER manual.', query = 'dishwasher',
        )
        self.assertIn('DISHWASHER', result)


class TestSearchReferences(TestCase):
    """End-to-end search via a mocked PaperlessClient."""

    def setUp(self):
        self.referencer = PaperlessExternalReferencer()

    def _envelope(self, *docs):
        return {'count': len(docs), 'results': list(docs)}

    def _doc(self, doc_id, **kwargs):
        d = {
            'id': doc_id,
            'title': f'Doc {doc_id}',
            'content': 'Some content text.',
            'mime_type': 'application/pdf',
        }
        d.update(kwargs)
        return d

    @patch('hi.services.paperless.pl_referencer.build_client')
    def test_empty_query_returns_empty_without_dispatch(self, mock_build):
        # Short-circuit so the picker can render a blank initial
        # modal without provoking an upstream call.
        result = self.referencer.search_references(query = '', limit = 20)
        self.assertEqual(result.results, [])
        self.assertIsNone(result.error_message)
        mock_build.assert_not_called()

    @patch('hi.services.paperless.pl_referencer.build_client')
    def test_whitespace_query_returns_empty(self, mock_build):
        result = self.referencer.search_references(query = '   ', limit = 20)
        self.assertEqual(result.results, [])
        self.assertIsNone(result.error_message)
        mock_build.assert_not_called()

    @patch('hi.services.paperless.pl_referencer.build_client')
    def test_translates_paperless_documents_to_results(self, mock_build):
        client = Mock()
        client.search_documents.return_value = self._envelope(
            self._doc(1, title = 'Warranty',
                      content = 'Warranty terms for the unit.'),
            self._doc(2, title = 'Manual',
                      content = 'Installation manual.', mime_type = 'text/plain'),
        )
        client.build_document_details_url.side_effect = (
            lambda id: f'https://p.example.com/documents/{id}/details/'
        )
        mock_build.return_value = client

        result = self.referencer.search_references(
            query = 'warranty', limit = 20,
        )

        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.results), 2)
        self.assertEqual(result.results[0].title, 'Warranty')
        self.assertEqual(
            result.results[0].source_url,
            'https://p.example.com/documents/1/details/',
        )
        # Thumbnail is the HI proxy URL, NOT the upstream URL — the
        # browser fetches via HI's session and HI fetches upstream
        # with the configured token.
        self.assertIn('/integration/services/paperless/documents/1/thumb/',
                      result.results[0].thumbnail_url)
        self.assertEqual(result.results[0].mime_type, 'application/pdf')
        self.assertIn('Warranty', result.results[0].snippet)

    @patch('hi.services.paperless.pl_referencer.build_client')
    def test_limit_is_passed_through_as_page_size(self, mock_build):
        client = Mock()
        client.search_documents.return_value = self._envelope()
        client.build_document_details_url.side_effect = (
            lambda id: f'https://p.example.com/documents/{id}/details/'
        )
        mock_build.return_value = client

        self.referencer.search_references(query = 'q', limit = 50)
        client.search_documents.assert_called_once_with(
            query = 'q', page_size = 50,
        )

    @patch('hi.services.paperless.pl_referencer.build_client')
    def test_missing_results_key_yields_empty(self, mock_build):
        # Defensive: don't blow up if upstream's envelope omits the
        # results key (or sends null).
        client = Mock()
        client.search_documents.return_value = {'count': 0}
        client.build_document_details_url.side_effect = (
            lambda id: f'https://p.example.com/documents/{id}/details/'
        )
        mock_build.return_value = client
        result = self.referencer.search_references(query = 'q', limit = 20)
        self.assertEqual(result.results, [])
        self.assertIsNone(result.error_message)


class TestSearchReferencesErrorMessages(TestCase):
    """Failure paths must surface ``error_message`` (not raise) so
    the picker can render a distinct banner instead of falling back
    to "no results."""

    def setUp(self):
        self.referencer = PaperlessExternalReferencer()

    @patch('hi.services.paperless.pl_referencer.build_client',
           side_effect = IntegrationAttributeError('not configured'))
    def test_unconfigured_integration(self, _mock_build):
        result = self.referencer.search_references(query = 'q', limit = 20)
        self.assertEqual(result.results, [])
        self.assertIn('not configured', result.error_message)

    @patch('hi.services.paperless.pl_referencer.build_client',
           side_effect = RuntimeError('boom in build'))
    def test_unexpected_client_build_error(self, _mock_build):
        result = self.referencer.search_references(query = 'q', limit = 20)
        self.assertEqual(result.results, [])
        self.assertIn('Paperless integration error', result.error_message)

    @patch('hi.services.paperless.pl_referencer.build_client')
    def test_http_401_names_token(self, mock_build):
        client = Mock()
        response = Mock()
        response.status_code = 401
        client.search_documents.side_effect = HTTPError('401', response = response)
        mock_build.return_value = client
        result = self.referencer.search_references(query = 'q', limit = 20)
        self.assertEqual(result.results, [])
        self.assertIn('401', result.error_message)
        self.assertIn('token', result.error_message.lower())

    @patch('hi.services.paperless.pl_referencer.build_client')
    def test_http_500_surfaces_status_code(self, mock_build):
        client = Mock()
        response = Mock()
        response.status_code = 500
        client.search_documents.side_effect = HTTPError('500', response = response)
        mock_build.return_value = client
        result = self.referencer.search_references(query = 'q', limit = 20)
        self.assertIn('500', result.error_message)

    @patch('hi.services.paperless.pl_referencer.build_client')
    def test_unexpected_search_exception(self, mock_build):
        client = Mock()
        client.search_documents.side_effect = RuntimeError('boom')
        mock_build.return_value = client
        result = self.referencer.search_references(query = 'q', limit = 20)
        self.assertEqual(result.results, [])
        self.assertIn('Paperless search failed', result.error_message)


class TestValidateConfiguration(TestCase):
    """``validate_configuration`` is the schema check delegated to
    ``pl_validation.validate_attributes`` (covered there in detail).
    Smoke-test that the referencer forwards correctly."""

    def setUp(self):
        self.integration = Integration.objects.create(
            integration_id = PaperlessMetaData.integration_id,
            is_enabled = True,
        )

    def test_success_when_attributes_valid(self):
        attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL,
                       'https://paperless.example.com/'),
            _make_attr(self.integration, PlAttributeType.API_TOKEN, 'token'),
        ]
        result = PaperlessExternalReferencer().validate_configuration(attrs)
        self.assertTrue(result.is_valid)

    def test_error_when_token_missing(self):
        attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL,
                       'https://paperless.example.com/'),
        ]
        result = PaperlessExternalReferencer().validate_configuration(attrs)
        self.assertFalse(result.is_valid)


class TestAttachReferences(TestCase):
    """End-to-end attach via a mocked PaperlessClient and a real
    Entity. Verifies the framework row is created and that the
    defensive thumbnail-fetch chain handles each failure mode
    gracefully (linking is the primary user goal)."""

    def setUp(self):
        from hi.apps.entity.enums import EntityType
        from hi.apps.entity.models import Entity
        self.entity = Entity.objects.create(
            name='Fridge', entity_type_str=str(EntityType.APPLIANCE),
        )
        self.referencer = PaperlessExternalReferencer()

    def tearDown(self):
        from hi.integrations.models import EntityExternalReference
        for row in EntityExternalReference.objects.filter(entity=self.entity):
            row.delete()

    def _selection(self, doc_id='42', title='Warranty',
                   source_url='https://p.example.com/documents/42/details/',
                   mime_type='application/pdf'):
        from hi.integrations.referencer.transient_models import (
            ExternalReferenceResult,
        )
        return ExternalReferenceResult(
            integration_key=IntegrationKey(
                integration_id=PaperlessMetaData.integration_id,
                integration_name=doc_id,
            ),
            title=title,
            source_url=source_url,
            mime_type=mime_type,
        )

    @patch.object(PaperlessExternalReferencer, 'build_client')
    def test_happy_path_creates_row_with_thumbnail(self, mock_build):
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.return_value = {
            'content': b'PNG-BYTES', 'mime_type': 'image/png',
        }
        mock_build.return_value = client

        self.referencer.attach_references(
            self.entity, [self._selection(doc_id='42')],
        )

        row = EntityExternalReference.objects.get(
            entity=self.entity,
            integration_id='paperless',
            integration_name='42',
        )
        self.assertEqual(row.title, 'Warranty')
        self.assertTrue(row.thumbnail.name)

    @patch.object(PaperlessExternalReferencer, 'build_client')
    def test_thumbnail_fail_original_fail_attaches_without_thumbnail(
            self, mock_build):
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.side_effect = HTTPError('500')
        client.download_original.side_effect = HTTPError('502')
        mock_build.return_value = client

        self.referencer.attach_references(
            self.entity, [self._selection(doc_id='99')],
        )

        row = EntityExternalReference.objects.get(
            entity=self.entity, integration_name='99',
        )
        self.assertFalse(row.thumbnail)

    @patch.object(ThumbnailHelpers, 'bytes_to_thumbnail_png',
                  return_value=b'GENERATED-PNG')
    @patch.object(PaperlessExternalReferencer, 'build_client')
    def test_thumbnail_fail_original_succeed_generate_succeed(
            self, mock_build, mock_generate):
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.side_effect = HTTPError('500')
        client.download_original.return_value = {
            'content': b'PDF-RAW', 'mime_type': 'application/pdf',
        }
        mock_build.return_value = client

        self.referencer.attach_references(
            self.entity, [self._selection(doc_id='99')],
        )

        row = EntityExternalReference.objects.get(
            entity=self.entity, integration_name='99',
        )
        self.assertTrue(row.thumbnail.name)
        mock_generate.assert_called_once_with(b'PDF-RAW', 'application/pdf')

    @patch.object(ThumbnailHelpers, 'bytes_to_thumbnail_png',
                  return_value=None)
    @patch.object(PaperlessExternalReferencer, 'build_client')
    def test_thumbnail_fail_original_succeed_generate_fail(
            self, mock_build, _mock_generate):
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.side_effect = HTTPError('500')
        client.download_original.return_value = {
            'content': b'PDF-RAW', 'mime_type': 'application/pdf',
        }
        mock_build.return_value = client

        self.referencer.attach_references(
            self.entity, [self._selection(doc_id='99')],
        )

        row = EntityExternalReference.objects.get(
            entity=self.entity, integration_name='99',
        )
        self.assertFalse(row.thumbnail)

    @patch.object(PaperlessExternalReferencer, 'build_client')
    def test_unsupported_mime_skips_original_fetch(self, mock_build):
        # Office docs / text / etc. the generator can't handle should
        # not trigger an original-bytes download just to discover the
        # generator will reject the bytes.
        from hi.integrations.models import EntityExternalReference
        client = Mock()
        client.download_thumbnail.side_effect = HTTPError('500')
        mock_build.return_value = client

        self.referencer.attach_references(
            self.entity,
            [self._selection(doc_id='99',
                             mime_type='application/vnd.oasis.opendocument.text')],
        )

        row = EntityExternalReference.objects.get(
            entity=self.entity, integration_name='99',
        )
        self.assertFalse(row.thumbnail)
        client.download_original.assert_not_called()

    @patch.object(PaperlessExternalReferencer, 'build_client',
                  side_effect=IntegrationAttributeError('not configured'))
    def test_client_build_failure_aborts_silently(self, _mock_build):
        from hi.integrations.models import EntityExternalReference
        self.referencer.attach_references(
            self.entity, [self._selection()],
        )
        self.assertEqual(
            EntityExternalReference.objects.filter(entity=self.entity).count(),
            0,
        )

    @patch.object(PaperlessExternalReferencer, 'build_client')
    def test_per_selection_exception_does_not_abort_batch(self, mock_build):
        from hi.integrations.models import EntityExternalReference
        # First selection has a non-numeric doc id; _try_upstream_thumbnail
        # returns None on the int cast, so the row still attaches. The
        # second selection succeeds normally. Verifies both end up
        # persisted.
        client = Mock()
        client.download_thumbnail.return_value = {
            'content': b'PNG', 'mime_type': 'image/png',
        }
        mock_build.return_value = client

        self.referencer.attach_references(
            self.entity, [
                self._selection(doc_id='not-numeric'),
                self._selection(doc_id='7'),
            ],
        )
        self.assertEqual(
            EntityExternalReference.objects.filter(entity=self.entity).count(),
            2,
        )
