"""Tests for the ATTRIBUTE_REFERENCE referencer.

Covers the two surfaces that matter for picker UX: snippet
extraction (window around the matched query, with paperless-style
fallbacks when no match) and the end-to-end translation of a
paperless documents-search response into AttributeReferenceResult
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
from hi.services.paperless.pl_referencer import PaperlessAttributeReferencer


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
            PaperlessAttributeReferencer._extract_snippet(
                content = '', query = 'q',
            )
        )

    def test_short_content_returned_verbatim(self):
        self.assertEqual(
            PaperlessAttributeReferencer._extract_snippet(
                content = 'Short doc text.', query = 'missing',
            ),
            'Short doc text.',
        )

    def test_long_content_without_match_truncates(self):
        result = PaperlessAttributeReferencer._extract_snippet(
            content = 'A' * 500, query = 'missing',
        )
        self.assertLessEqual(len(result), 161)  # 160 + the ellipsis
        self.assertTrue(result.endswith('…'))

    def test_match_in_middle_emits_leading_and_trailing_ellipses(self):
        content = 'x' * 200 + ' DISHWASHER ' + 'y' * 200
        result = PaperlessAttributeReferencer._extract_snippet(
            content = content, query = 'dishwasher',
        )
        self.assertIn('DISHWASHER', result)
        self.assertTrue(result.startswith('…'))
        self.assertTrue(result.endswith('…'))

    def test_match_at_start_no_leading_ellipsis(self):
        result = PaperlessAttributeReferencer._extract_snippet(
            content = 'Warranty info follows.', query = 'warranty',
        )
        self.assertFalse(result.startswith('…'))

    def test_case_insensitive_match(self):
        result = PaperlessAttributeReferencer._extract_snippet(
            content = 'The DISHWASHER manual.', query = 'dishwasher',
        )
        self.assertIn('DISHWASHER', result)


class TestSearchReferences(TestCase):
    """End-to-end search via a mocked PaperlessClient."""

    def setUp(self):
        self.referencer = PaperlessAttributeReferencer()

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
        self.referencer = PaperlessAttributeReferencer()

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
        result = PaperlessAttributeReferencer().validate_configuration(attrs)
        self.assertTrue(result.is_valid)

    def test_error_when_token_missing(self):
        attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL,
                       'https://paperless.example.com/'),
        ]
        result = PaperlessAttributeReferencer().validate_configuration(attrs)
        self.assertFalse(result.is_valid)
