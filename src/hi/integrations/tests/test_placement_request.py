"""
Direct unit tests for ``PlacementUrlParams``.

The class is the single source of truth for the placement view's
URL/form-param contract — key names, value encodings, list
separators, parser. Most behaviors are exercised indirectly through
view tests, but pinning the class directly catches contract drift
(e.g., a key rename, an encoding change, a sloppy parser fix) before
it cascades into hard-to-trace view-level test failures.
"""
import logging

from django.core.exceptions import BadRequest
from django.http import QueryDict
from django.test import SimpleTestCase

from hi.integrations.placement_request import PlacementUrlParams

logging.disable(logging.CRITICAL)


class PlacementUrlParamsToQueryDictTests(SimpleTestCase):

    def test_defaults_produce_empty_dict(self):
        """Sparse encoding: a default-constructed params object
        contributes no query keys. Keeps URLs free of redundant
        ``?is_initial_import=0`` cruft."""
        params = PlacementUrlParams()
        self.assertEqual(params.to_query_dict(), {})

    def test_is_initial_import_only_emits_its_key(self):
        params = PlacementUrlParams(is_initial_import=True)
        self.assertEqual(
            params.to_query_dict(),
            {PlacementUrlParams.KEY_IS_INITIAL_IMPORT: PlacementUrlParams.TRUE_VALUE},
        )

    def test_entity_ids_only_emits_its_key(self):
        params = PlacementUrlParams(entity_ids=[1, 2, 3])
        self.assertEqual(
            params.to_query_dict(),
            {PlacementUrlParams.KEY_ENTITY_IDS: '1,2,3'},
        )

    def test_both_fields_populated(self):
        params = PlacementUrlParams(is_initial_import=True, entity_ids=[7, 8])
        self.assertEqual(
            params.to_query_dict(),
            {
                PlacementUrlParams.KEY_IS_INITIAL_IMPORT: PlacementUrlParams.TRUE_VALUE,
                PlacementUrlParams.KEY_ENTITY_IDS: '7,8',
            },
        )


class PlacementUrlParamsAppendToUrlTests(SimpleTestCase):

    def test_default_params_append_no_query_string(self):
        params = PlacementUrlParams()
        self.assertEqual(
            params.append_to_url('/placement/test'),
            '/placement/test',
        )

    def test_populated_params_append_url_encoded_query(self):
        """Goes through ``django.utils.http.urlencode`` so the
        comma in ``entity_ids`` is encoded to %2C — protects against
        any future field whose value contains URL-reserved chars."""
        params = PlacementUrlParams(is_initial_import=True, entity_ids=[1, 2])
        url = params.append_to_url('/placement/test')
        self.assertTrue(url.startswith('/placement/test?'))
        self.assertIn('is_initial_import=1', url)
        # Comma is URL-encoded by urlencode.
        self.assertIn('entity_ids=1%2C2', url)


class PlacementUrlParamsFromDataTests(SimpleTestCase):

    def test_empty_data_returns_default_params(self):
        result = PlacementUrlParams.from_data(QueryDict(''))
        self.assertEqual(result, PlacementUrlParams())

    def test_round_trip_preserves_values(self):
        """The contract guarantee: ``to_query_dict`` →
        ``QueryDict`` → ``from_data`` reconstructs an equivalent
        params object. Any encoder/decoder asymmetry breaks this."""
        original = PlacementUrlParams(is_initial_import=True, entity_ids=[3, 1, 4])
        qd = QueryDict(mutable=True)
        for k, v in original.to_query_dict().items():
            qd[k] = v
        roundtripped = PlacementUrlParams.from_data(qd)
        self.assertEqual(original, roundtripped)

    def test_is_initial_import_accepts_robust_truthy_spellings(self):
        """``str_to_bool`` accepts '1', 'true', 'yes', etc. so a
        hand-crafted URL or a future encoding change on the producer
        side doesn't silently parse as False."""
        for truthy in ('1', 'true', 'TRUE', 'yes', 'on'):
            with self.subTest(value=truthy):
                qd = QueryDict(f'is_initial_import={truthy}')
                self.assertTrue(PlacementUrlParams.from_data(qd).is_initial_import)

    def test_is_initial_import_falsy_values(self):
        """Anything not-truthy parses as False, including the
        canonical FALSE_VALUE encoding and absence."""
        for falsy in ('0', 'false', 'no', '', 'garbage'):
            with self.subTest(value=falsy):
                qd = QueryDict(f'is_initial_import={falsy}')
                self.assertFalse(PlacementUrlParams.from_data(qd).is_initial_import)

    def test_entity_ids_parses_comma_separated_integers(self):
        qd = QueryDict('entity_ids=10,20,30')
        result = PlacementUrlParams.from_data(qd)
        self.assertEqual(result.entity_ids, [10, 20, 30])

    def test_entity_ids_tolerates_whitespace_around_tokens(self):
        """The parser uses ``int(piece)`` which strips its own
        whitespace. Defensive — guards against a producer that
        accidentally introduces spaces."""
        qd = QueryDict('entity_ids=10, 20 ,30')
        result = PlacementUrlParams.from_data(qd)
        self.assertEqual(result.entity_ids, [10, 20, 30])

    def test_entity_ids_malformed_raises_bad_request(self):
        """Tampered input fails loudly rather than silently
        widening scope (e.g., dropping the unparseable id and
        proceeding with a partial set)."""
        qd = QueryDict('entity_ids=1,abc,3')
        with self.assertRaises(BadRequest):
            PlacementUrlParams.from_data(qd)

    def test_entity_ids_absent_returns_empty_list(self):
        qd = QueryDict('is_initial_import=1')
        result = PlacementUrlParams.from_data(qd)
        self.assertEqual(result.entity_ids, [])


class PlacementUrlParamsFormValueTests(SimpleTestCase):

    def test_is_initial_import_form_value_true_returns_true_value(self):
        params = PlacementUrlParams(is_initial_import=True)
        self.assertEqual(
            params.is_initial_import_form_value(),
            PlacementUrlParams.TRUE_VALUE,
        )

    def test_is_initial_import_form_value_false_returns_false_value(self):
        params = PlacementUrlParams(is_initial_import=False)
        self.assertEqual(
            params.is_initial_import_form_value(),
            PlacementUrlParams.FALSE_VALUE,
        )
