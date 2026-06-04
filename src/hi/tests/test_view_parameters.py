"""
Focused tests for ViewParameters' transient SVG geometry tracking - the
pan/zoom state that operations like EntityAddView preserve. The behavior
under test is the clear-on-context-shift logic and session round-trip; the
rest of ViewParameters (view/collection resolution) is covered elsewhere.
"""
import logging

from hi.apps.common.svg_models import SvgViewBox
from hi.apps.location.tests.synthetic_data import LocationSyntheticData
from hi.testing.base_test_case import BaseTestCase, MockRequest
from hi.view_parameters import ViewParameters

logging.disable(logging.CRITICAL)


class TestViewParametersLastSvgGeometry(BaseTestCase):

    def _view_parameters_with_geometry(self, location_view) -> ViewParameters:
        view_parameters = ViewParameters()
        view_parameters.location_view_id = location_view.id
        view_parameters.set_last_svg_geometry(
            svg_view_box = SvgViewBox( x = 10, y = 20, width = 30, height = 40 ),
            svg_rotate = '15',
        )
        return view_parameters

    def test_switching_location_view_clears_geometry(self):
        # A different LocationView frames the same coordinate space
        # differently, so the preserved pan/zoom must be dropped.
        location_view_1 = LocationSyntheticData.create_test_location_view()
        location_view_2 = LocationSyntheticData.create_test_location_view(
            location = location_view_1.location )
        view_parameters = self._view_parameters_with_geometry( location_view_1 )

        view_parameters.update_location_view( location_view_2 )

        self.assertIsNone( view_parameters.last_svg_view_box )
        self.assertIsNone( view_parameters.last_svg_rotate )

    def test_same_location_view_preserves_geometry(self):
        # Same-id re-render (e.g. the post-add redirect) must NOT clear,
        # or the geometry it is preserving would be lost.
        location_view = LocationSyntheticData.create_test_location_view()
        view_parameters = self._view_parameters_with_geometry( location_view )

        view_parameters.update_location_view( location_view )

        self.assertIsNotNone( view_parameters.last_svg_view_box )
        self.assertEqual( view_parameters.last_svg_rotate, '15' )

    def test_unsetting_location_view_clears_geometry(self):
        location_view = LocationSyntheticData.create_test_location_view()
        view_parameters = self._view_parameters_with_geometry( location_view )

        view_parameters.update_location_view( None )

        self.assertIsNone( view_parameters.last_svg_view_box )
        self.assertIsNone( view_parameters.last_svg_rotate )

    def test_switching_to_collection_clears_geometry(self):
        # Any move to a Collection view is a context shift; location
        # pan/zoom no longer applies.
        location_view = LocationSyntheticData.create_test_location_view()
        view_parameters = self._view_parameters_with_geometry( location_view )

        view_parameters.update_collection( None )

        self.assertIsNone( view_parameters.last_svg_view_box )
        self.assertIsNone( view_parameters.last_svg_rotate )

    def test_session_round_trip_preserves_geometry(self):
        location_view = LocationSyntheticData.create_test_location_view()
        view_parameters = self._view_parameters_with_geometry( location_view )
        request = MockRequest()

        view_parameters.to_session( request )
        restored = ViewParameters.from_session( request )

        self.assertEqual( restored.last_svg_view_box.to_dict(),
                          view_parameters.last_svg_view_box.to_dict() )
        self.assertEqual( restored.last_svg_rotate, '15' )

    def test_session_round_trip_without_geometry(self):
        request = MockRequest()

        ViewParameters().to_session( request )
        restored = ViewParameters.from_session( request )

        self.assertIsNone( restored.last_svg_view_box )
        self.assertIsNone( restored.last_svg_rotate )


class TestViewParametersSnapGrid(BaseTestCase):
    """The snap-grid user preference: round-trips through the session,
    preserves an explicit 0 (snapping disabled), and falls back to the
    default only when the key is missing/malformed."""

    def test_round_trip_preserves_value(self):
        view_parameters = ViewParameters()
        view_parameters.svg_snap_grid_pixels = 12
        request = MockRequest()
        view_parameters.to_session( request )
        self.assertEqual(
            ViewParameters.from_session( request ).svg_snap_grid_pixels, 12 )

    def test_explicit_zero_preserved(self):
        view_parameters = ViewParameters()
        view_parameters.svg_snap_grid_pixels = 0
        request = MockRequest()
        view_parameters.to_session( request )
        self.assertEqual(
            ViewParameters.from_session( request ).svg_snap_grid_pixels, 0 )

    def test_missing_key_falls_back_to_default(self):
        restored = ViewParameters.from_session( MockRequest() )
        self.assertEqual(
            restored.svg_snap_grid_pixels,
            ViewParameters.DEFAULT_SVG_SNAP_GRID_PIXELS )
