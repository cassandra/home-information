import logging
import os
import shutil
import tempfile

from django.core.files.storage import default_storage
from django.test import override_settings
from django.urls import reverse

from hi.apps.location.location_manager import LocationManager
from hi.apps.location.tests.synthetic_data import LocationSyntheticData
from hi.enums import ViewMode
from hi.testing.view_test_base import DualModeViewTestCase

logging.disable(logging.CRITICAL)


class LocationSvgEditViewTestBase(DualModeViewTestCase):
    """
    Shared setup for all SVG editor view tests.

    Creates a location with a real SVG file in an isolated media root
    and enables edit mode in the session.
    """

    LIVE_SVG_CONTENT = '<rect width="800" height="600" fill="white"/>'

    def setUp(self):
        super().setUp()
        self.setSessionViewMode(ViewMode.EDIT)

        # Set up isolated MEDIA_ROOT
        self._temp_media_dir = tempfile.mkdtemp()
        self._settings_patcher = override_settings(MEDIA_ROOT=self._temp_media_dir)
        self._settings_patcher.enable()

        self.location = LocationSyntheticData.create_test_location(
            name='Test Location',
            svg_fragment_filename='location/svg/test-location.svg',
            svg_view_box_str='0 0 800 600',
        )
        self._write_live_svg()
        self.manager = LocationManager()

    def tearDown(self):
        if hasattr(self, '_settings_patcher'):
            self._settings_patcher.disable()
        if hasattr(self, '_temp_media_dir'):
            shutil.rmtree(self._temp_media_dir, ignore_errors=True)
        LocationManager._instance = None
        super().tearDown()

    def _write_live_svg(self, content=None):
        """Write the live SVG file into the isolated media root."""
        if content is None:
            content = self.LIVE_SVG_CONTENT
        filepath = self.location.svg_fragment_filename
        full_dir = os.path.dirname(os.path.join(self._temp_media_dir, filepath))
        os.makedirs(full_dir, exist_ok=True)
        with default_storage.open(filepath, 'w') as f:
            f.write(content)

    def _create_draft(self, content=None):
        """Create a draft file, optionally with different content."""
        self.manager.create_draft_svg(self.location)
        if content is not None:
            self.manager.save_draft_svg(self.location, content)


class TestLocationSvgEditView(LocationSvgEditViewTestBase):
    """Tests for LocationSvgEditView - GET creates draft and renders editor page."""

    def test_get_creates_draft_and_renders_editor(self):
        """GET should create a draft file and render the SVG editor page."""
        url = reverse('location_edit_svg_edit', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateRendered(response, 'location/edit/pages/location_svg_edit.html')
        self.assertTrue(self.manager.draft_svg_exists(self.location))

    def test_get_sets_draft_svg_filename_in_context(self):
        """GET should include draft_svg_filename in the template context."""
        url = reverse('location_edit_svg_edit', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertIn('draft_svg_filename', response.context)
        expected_draft = self.manager.get_draft_svg_filename(self.location)
        self.assertEqual(response.context['draft_svg_filename'], expected_draft)

    def test_get_preserves_existing_draft(self):
        """GET should not overwrite an existing draft with changes."""
        edited_content = '<circle r="50"/>'
        self._create_draft(edited_content)

        url = reverse('location_edit_svg_edit', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # draft_resumed should be True since draft differs from live
        self.assertTrue(response.context['draft_resumed'])

        # Verify draft content was not overwritten
        draft_filename = self.manager.get_draft_svg_filename(self.location)
        with default_storage.open(draft_filename, 'r') as f:
            content = f.read()
        self.assertEqual(content, edited_content)

    def test_get_sets_viewbox_in_session(self):
        """GET should store the SVG viewbox in the session."""
        url = reverse('location_edit_svg_edit', kwargs={'location_id': self.location.id})
        self.client.get(url)

        session_key = f'svg_edit_viewbox_{self.location.id}'
        session = self.client.session
        self.assertEqual(session[session_key], self.location.svg_view_box_str)

    def test_get_nonexistent_location_returns_404(self):
        """GET with invalid location_id should return 404."""
        url = reverse('location_edit_svg_edit', kwargs={'location_id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class TestLocationSvgEditCancelView(LocationSvgEditViewTestBase):
    """Tests for LocationSvgEditCancelView - cancel editing workflow."""

    def test_get_no_changes_redirects_directly(self):
        """GET with no draft changes should redirect without showing modal."""
        self._create_draft()  # Draft matches live

        # Set the session viewbox to match the location (as the edit view would)
        session = self.client.session
        session_key = f'svg_edit_viewbox_{self.location.id}'
        session[session_key] = self.location.svg_view_box_str
        session.save()

        url = reverse('location_svg_edit_cancel', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        # Should clean up draft
        self.assertFalse(self.manager.draft_svg_exists(self.location))

    def test_get_with_changes_shows_modal(self):
        """GET with draft changes should show confirmation modal."""
        self._create_draft('<circle r="999"/>')

        url = reverse('location_svg_edit_cancel', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_svg_edit_cancel.html')

    def test_post_deletes_draft_and_redirects(self):
        """POST should delete draft and redirect to home."""
        self._create_draft('<circle r="999"/>')

        url = reverse('location_svg_edit_cancel', kwargs={'location_id': self.location.id})
        response = self.client.post(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        self.assertFalse(self.manager.draft_svg_exists(self.location))

    def test_post_does_not_modify_live_svg(self):
        """POST cancel should leave the live SVG file unchanged."""
        self._create_draft('<circle r="999"/>')

        url = reverse('location_svg_edit_cancel', kwargs={'location_id': self.location.id})
        self.client.post(url)

        with default_storage.open(self.location.svg_fragment_filename, 'r') as f:
            live_content = f.read()
        self.assertEqual(live_content, self.LIVE_SVG_CONTENT)


class TestLocationSvgEditExitView(LocationSvgEditViewTestBase):
    """Tests for LocationSvgEditExitView - save and exit workflow."""

    def test_get_no_changes_redirects_directly(self):
        """GET with no draft changes should redirect without showing modal."""
        self._create_draft()  # Draft matches live

        # Set the session viewbox to match the location (as the edit view would)
        session = self.client.session
        session_key = f'svg_edit_viewbox_{self.location.id}'
        session[session_key] = self.location.svg_view_box_str
        session.save()

        url = reverse('location_svg_edit_exit', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)

    def test_get_with_changes_shows_modal(self):
        """GET with draft changes should show confirmation modal."""
        self._create_draft('<circle r="999"/>')

        url = reverse('location_svg_edit_exit', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_svg_edit_exit.html')

    def test_post_commits_draft_to_live(self):
        """POST should commit draft content to the live SVG file."""
        edited_content = '<ellipse rx="100" ry="50"/>'
        self._create_draft(edited_content)

        url = reverse('location_svg_edit_exit', kwargs={'location_id': self.location.id})
        self.client.post(url)

        with default_storage.open(self.location.svg_fragment_filename, 'r') as f:
            live_content = f.read()
        self.assertEqual(live_content, edited_content)

    def test_post_removes_draft_file(self):
        """POST should remove the draft file after committing."""
        self._create_draft('<circle r="50"/>')

        url = reverse('location_svg_edit_exit', kwargs={'location_id': self.location.id})
        self.client.post(url)

        self.assertFalse(self.manager.draft_svg_exists(self.location))

    def test_post_saves_viewbox_from_session(self):
        """POST should save the session viewbox to the location model."""
        self._create_draft('<circle r="50"/>')

        # Set a different viewbox in the session
        session = self.client.session
        session_key = f'svg_edit_viewbox_{self.location.id}'
        session[session_key] = '0 0 1200 900'
        session.save()

        url = reverse('location_svg_edit_exit', kwargs={'location_id': self.location.id})
        self.client.post(url)

        self.location.refresh_from_db()
        self.assertEqual(self.location.svg_view_box_str, '0 0 1200 900')


class TestLocationSvgEditRevertView(LocationSvgEditViewTestBase):
    """Tests for LocationSvgEditRevertView - revert draft to live content."""

    def test_get_no_changes_returns_no_content(self):
        """GET with no changes returns 204 No Content (nothing to revert)."""
        self._create_draft()  # Draft matches live

        # Set the session viewbox to match the location (as the edit view would)
        session = self.client.session
        session_key = f'svg_edit_viewbox_{self.location.id}'
        session[session_key] = self.location.svg_view_box_str
        session.save()

        url = reverse('location_svg_edit_revert', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertEqual(response.status_code, 204)

    def test_get_with_changes_shows_confirmation_modal(self):
        """GET with changes should show revert confirmation modal."""
        self._create_draft('<circle r="999"/>')

        url = reverse('location_svg_edit_revert', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_svg_edit_revert.html')

    def test_post_copies_live_to_draft(self):
        """POST should overwrite draft with live SVG content."""
        self._create_draft('<circle r="999"/>')

        url = reverse('location_svg_edit_revert', kwargs={'location_id': self.location.id})
        self.client.post(url)

        draft_filename = self.manager.get_draft_svg_filename(self.location)
        with default_storage.open(draft_filename, 'r') as f:
            draft_content = f.read()
        self.assertEqual(draft_content, self.LIVE_SVG_CONTENT)

    def test_post_resets_session_viewbox(self):
        """POST should reset the session viewbox to the location's original."""
        self._create_draft('<circle r="999"/>')

        session = self.client.session
        session_key = f'svg_edit_viewbox_{self.location.id}'
        session[session_key] = '0 0 9999 9999'
        session.save()

        url = reverse('location_svg_edit_revert', kwargs={'location_id': self.location.id})
        self.client.post(url)

        session = self.client.session
        self.assertEqual(session[session_key], self.location.svg_view_box_str)


class TestLocationSvgEditSaveView(LocationSvgEditViewTestBase):
    """Tests for LocationSvgEditSaveView - save SVG content to draft."""

    def test_post_saves_content_to_draft(self):
        """POST should write svg_content to the draft file."""
        new_content = '<g><text>Hello</text></g>'
        url = reverse('location_svg_edit_save', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'svg_content': new_content})

        self.assertEqual(response.status_code, 200)

        draft_filename = self.manager.get_draft_svg_filename(self.location)
        with default_storage.open(draft_filename, 'r') as f:
            saved = f.read()
        self.assertEqual(saved, new_content)

    def test_post_without_content_returns_400(self):
        """POST without svg_content should return 400 Bad Request."""
        url = reverse('location_svg_edit_save', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_post_does_not_modify_live_svg(self):
        """POST save should only affect the draft, not the live file."""
        url = reverse('location_svg_edit_save', kwargs={'location_id': self.location.id})
        self.client.post(url, {'svg_content': '<circle r="999"/>'})

        with default_storage.open(self.location.svg_fragment_filename, 'r') as f:
            live_content = f.read()
        self.assertEqual(live_content, self.LIVE_SVG_CONTENT)

    def test_get_not_allowed(self):
        """GET should return 405 Method Not Allowed."""
        url = reverse('location_svg_edit_save', kwargs={'location_id': self.location.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class TestLocationSvgEditExportView(LocationSvgEditViewTestBase):
    """Tests for LocationSvgEditExportView - export draft SVG as download."""

    def test_get_returns_svg_file_download(self):
        """GET should return an SVG file attachment response."""
        self._create_draft()

        url = reverse('location_svg_edit_export', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_get_includes_viewbox_and_svg_wrapper(self):
        """GET should wrap draft content in a full SVG document with viewBox."""
        self._create_draft()

        url = reverse('location_svg_edit_export', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        content = response.content.decode('utf-8')
        self.assertIn('viewBox="0 0 800 600"', content)
        self.assertIn('<svg', content)
        self.assertIn('</svg>', content)
        self.assertIn(self.LIVE_SVG_CONTENT, content)

    def test_get_uses_session_viewbox_if_available(self):
        """GET should use session viewbox instead of location's default."""
        self._create_draft()

        session = self.client.session
        session_key = f'svg_edit_viewbox_{self.location.id}'
        session[session_key] = '0 0 1600 1200'
        session.save()

        url = reverse('location_svg_edit_export', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        content = response.content.decode('utf-8')
        self.assertIn('viewBox="0 0 1600 1200"', content)

    def test_get_filename_derived_from_location_name(self):
        """The download filename should be derived from the location name."""
        self._create_draft()

        url = reverse('location_svg_edit_export', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertIn('background-test-location.svg', response['Content-Disposition'])

    def test_get_without_draft_returns_400(self):
        """GET without an existing draft should return 400."""
        url = reverse('location_svg_edit_export', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)


class TestLocationSvgEditViewBoxView(LocationSvgEditViewTestBase):
    """Tests for LocationSvgEditViewBoxView - update session viewbox."""

    def test_post_updates_session_viewbox(self):
        """POST should store the new viewbox dimensions in the session."""
        self._create_draft()

        url = reverse('location_svg_edit_viewbox', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'width': '1200', 'height': '900'})

        self.assertEqual(response.status_code, 200)

        session = self.client.session
        session_key = f'svg_edit_viewbox_{self.location.id}'
        self.assertIn('1200', session[session_key])
        self.assertIn('900', session[session_key])

    def test_post_returns_canvas_html(self):
        """POST should return HTML content for the SVG canvas pane."""
        self._create_draft()

        url = reverse('location_svg_edit_viewbox', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'width': '1200', 'height': '900'})

        self.assertEqual(response.status_code, 200)
        # Response should be HTML (canvas template)
        content_type = response['Content-Type']
        self.assertIn('text/html', content_type)

    def test_post_invalid_dimensions_returns_400(self):
        """POST with non-positive dimensions should return 400."""
        url = reverse('location_svg_edit_viewbox', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'width': '0', 'height': '100'})
        self.assertEqual(response.status_code, 400)

    def test_post_negative_dimensions_returns_400(self):
        """POST with negative dimensions should return 400."""
        url = reverse('location_svg_edit_viewbox', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'width': '-100', 'height': '100'})
        self.assertEqual(response.status_code, 400)

    def test_post_non_numeric_dimensions_returns_400(self):
        """POST with non-numeric dimensions should return 400."""
        url = reverse('location_svg_edit_viewbox', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {'width': 'abc', 'height': '100'})
        self.assertEqual(response.status_code, 400)

    def test_does_not_change_location_model(self):
        """POST should only update the session, not the database."""
        self._create_draft()
        original_viewbox = self.location.svg_view_box_str

        url = reverse('location_svg_edit_viewbox', kwargs={'location_id': self.location.id})
        self.client.post(url, {'width': '9999', 'height': '9999'})

        self.location.refresh_from_db()
        self.assertEqual(self.location.svg_view_box_str, original_viewbox)


class TestLocationSvgBackgroundView(LocationSvgEditViewTestBase):
    """Tests for LocationSvgBackgroundView - background options modal."""

    def test_get_shows_background_modal(self):
        """GET should render the background options modal."""
        url = reverse('location_svg_background', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_svg_background.html')

    def test_get_async_returns_json_with_modal(self):
        """AJAX GET should return JSON with modal content."""
        url = reverse('location_svg_background', kwargs={'location_id': self.location.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        data = response.json()
        self.assertIn('modal', data)

    def test_get_includes_location_in_context(self):
        """GET should include the location object in template context."""
        url = reverse('location_svg_background', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertEqual(response.context['location'], self.location)


class TestLocationSvgTemplateSelectView(LocationSvgEditViewTestBase):
    """Tests for LocationSvgTemplateSelectView - SVG template selection."""

    def test_get_shows_template_selection_modal(self):
        """GET should render the template selection modal."""
        url = reverse('location_svg_template_select', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'location/edit/modals/location_svg_template_select.html')

    def test_get_includes_templates_in_context(self):
        """GET should include available templates in context."""
        url = reverse('location_svg_template_select', kwargs={'location_id': self.location.id})
        response = self.client.get(url)

        self.assertIn('svg_templates', response.context)
        self.assertIsInstance(response.context['svg_templates'], list)

    def test_post_without_template_name_returns_400(self):
        """POST without a template_name should return 400."""
        url = reverse('location_svg_template_select', kwargs={'location_id': self.location.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 400)

    def test_get_nonexistent_location_returns_404(self):
        """GET with invalid location_id should return 404."""
        url = reverse('location_svg_template_select', kwargs={'location_id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
