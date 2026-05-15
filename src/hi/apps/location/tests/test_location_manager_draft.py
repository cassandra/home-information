import logging
import os

from django.core.files.storage import default_storage

from hi.apps.location.location_manager import LocationManager
from hi.apps.location.tests.synthetic_data import LocationSyntheticData
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestLocationManagerDraftSvgHelpers(BaseTestCase):
    """
    Tests for LocationManager draft SVG file operations.

    These methods manage a draft copy of a location's SVG file for
    in-place editing, allowing save/revert/commit workflows.
    """

    def setUp(self):
        super().setUp()
        self.manager = LocationManager()
        self.location = LocationSyntheticData.create_test_location(
            svg_fragment_filename='location/svg/my-location-12345.svg',
            svg_view_box_str='0 0 800 600',
        )
        self.live_svg_content = '<rect width="800" height="600" fill="white"/>'

    def _write_live_svg(self, temp_media, content=None):
        """Helper to write the live SVG file into the isolated media root."""
        if content is None:
            content = self.live_svg_content
        filepath = self.location.svg_fragment_filename
        full_dir = os.path.dirname(os.path.join(temp_media, filepath))
        os.makedirs(full_dir, exist_ok=True)
        with default_storage.open(filepath, 'w') as f:
            f.write(content)

    def test_get_draft_svg_filename_inserts_draft_before_extension(self):
        """Draft filename should insert '.draft' before the '.svg' extension."""
        result = self.manager.get_draft_svg_filename(self.location)
        self.assertEqual(result, 'location/svg/my-location-12345.draft.svg')

    def test_get_draft_svg_filename_handles_no_extension(self):
        """Draft filename derivation should work even without an extension."""
        self.location.svg_fragment_filename = 'location/svg/noext'
        result = self.manager.get_draft_svg_filename(self.location)
        self.assertEqual(result, 'location/svg/noext.draft')

    def test_draft_svg_exists_returns_false_when_no_draft(self):
        """draft_svg_exists returns False when no draft file has been created."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.assertFalse(self.manager.draft_svg_exists(self.location))

    def test_draft_svg_exists_returns_true_after_create(self):
        """draft_svg_exists returns True after create_draft_svg is called."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.manager.create_draft_svg(self.location)
            self.assertTrue(self.manager.draft_svg_exists(self.location))

    def test_create_draft_svg_copies_live_content(self):
        """create_draft_svg should copy the live SVG content to the draft file."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            draft_filename = self.manager.create_draft_svg(self.location)

            with default_storage.open(draft_filename, 'r') as f:
                draft_content = f.read()
            self.assertEqual(draft_content, self.live_svg_content)

    def test_create_draft_svg_returns_draft_filename(self):
        """create_draft_svg should return the draft filename path."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            draft_filename = self.manager.create_draft_svg(self.location)
            expected = self.manager.get_draft_svg_filename(self.location)
            self.assertEqual(draft_filename, expected)

    def test_draft_has_changes_returns_false_when_no_draft(self):
        """draft_has_changes returns False when no draft file exists."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.assertFalse(self.manager.draft_has_changes(self.location))

    def test_draft_has_changes_returns_false_when_identical(self):
        """draft_has_changes returns False when draft matches live content."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.manager.create_draft_svg(self.location)
            self.assertFalse(self.manager.draft_has_changes(self.location))

    def test_draft_has_changes_returns_true_when_different(self):
        """draft_has_changes returns True when draft content differs from live."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.manager.create_draft_svg(self.location)
            self.manager.save_draft_svg(self.location, '<circle r="50"/>')
            self.assertTrue(self.manager.draft_has_changes(self.location))

    def test_save_draft_svg_writes_content(self):
        """save_draft_svg writes the given content to the draft file."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            new_content = '<circle cx="100" cy="100" r="50"/>'
            self.manager.save_draft_svg(self.location, new_content)

            draft_filename = self.manager.get_draft_svg_filename(self.location)
            with default_storage.open(draft_filename, 'r') as f:
                saved_content = f.read()
            self.assertEqual(saved_content, new_content)

    def test_save_draft_svg_overwrites_existing_draft(self):
        """save_draft_svg overwrites previous draft content."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.manager.save_draft_svg(self.location, 'first version')
            self.manager.save_draft_svg(self.location, 'second version')

            draft_filename = self.manager.get_draft_svg_filename(self.location)
            with default_storage.open(draft_filename, 'r') as f:
                saved_content = f.read()
            self.assertEqual(saved_content, 'second version')

    def test_delete_draft_svg_removes_file(self):
        """delete_draft_svg removes the draft file."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.manager.create_draft_svg(self.location)
            self.assertTrue(self.manager.draft_svg_exists(self.location))

            self.manager.delete_draft_svg(self.location)
            self.assertFalse(self.manager.draft_svg_exists(self.location))

    def test_delete_draft_svg_is_safe_when_no_draft(self):
        """delete_draft_svg should not raise when no draft file exists."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            # Should not raise
            self.manager.delete_draft_svg(self.location)

    def test_commit_draft_svg_copies_draft_to_live(self):
        """commit_draft_svg should overwrite live file with draft content."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.manager.create_draft_svg(self.location)

            edited_content = '<ellipse cx="400" cy="300" rx="200" ry="100"/>'
            self.manager.save_draft_svg(self.location, edited_content)
            self.manager.commit_draft_svg(self.location)

            with default_storage.open(self.location.svg_fragment_filename, 'r') as f:
                live_content = f.read()
            self.assertEqual(live_content, edited_content)

    def test_commit_draft_svg_removes_draft_file(self):
        """commit_draft_svg should delete the draft file after copying."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.manager.create_draft_svg(self.location)
            self.manager.commit_draft_svg(self.location)
            self.assertFalse(self.manager.draft_svg_exists(self.location))

    def test_commit_draft_svg_leaves_live_unchanged_if_draft_matches(self):
        """commit_draft_svg with unmodified draft preserves original live content."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)
            self.manager.create_draft_svg(self.location)
            self.manager.commit_draft_svg(self.location)

            with default_storage.open(self.location.svg_fragment_filename, 'r') as f:
                live_content = f.read()
            self.assertEqual(live_content, self.live_svg_content)

    def test_full_edit_workflow(self):
        """End-to-end: create draft, edit, save, commit, verify live updated."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)

            # Step 1: Create draft
            self.manager.create_draft_svg(self.location)
            self.assertTrue(self.manager.draft_svg_exists(self.location))
            self.assertFalse(self.manager.draft_has_changes(self.location))

            # Step 2: Edit draft
            edited = '<g><text>Edited</text></g>'
            self.manager.save_draft_svg(self.location, edited)
            self.assertTrue(self.manager.draft_has_changes(self.location))

            # Step 3: Commit
            self.manager.commit_draft_svg(self.location)
            self.assertFalse(self.manager.draft_svg_exists(self.location))

            # Step 4: Verify live content updated
            with default_storage.open(self.location.svg_fragment_filename, 'r') as f:
                live_content = f.read()
            self.assertEqual(live_content, edited)

    def test_cancel_workflow_discards_changes(self):
        """End-to-end: create draft, edit, delete draft, verify live unchanged."""
        with self.isolated_media_root() as temp_media:
            self._write_live_svg(temp_media)

            self.manager.create_draft_svg(self.location)
            self.manager.save_draft_svg(self.location, '<g>CHANGED</g>')
            self.assertTrue(self.manager.draft_has_changes(self.location))

            # Cancel: delete draft
            self.manager.delete_draft_svg(self.location)
            self.assertFalse(self.manager.draft_svg_exists(self.location))

            # Live content should be unchanged
            with default_storage.open(self.location.svg_fragment_filename, 'r') as f:
                live_content = f.read()
            self.assertEqual(live_content, self.live_svg_content)


class TestLocationManagerCreateLocationView(BaseTestCase):
    """create_location_view auto-disambiguates duplicate names within
    a Location by appending a numeric suffix. Used both by the
    dispatcher's '+ New view: "<integration label>"' option (when
    the operator already has a view with that name) and by the
    manage-page Add View form (when the operator types a
    duplicate)."""

    def setUp(self):
        super().setUp()
        from hi.apps.location.models import Location
        self.location = Location.objects.create(
            name='Test Location', svg_view_box_str='0 0 100 100',
        )
        self.manager = LocationManager()

    def test_unique_name_passes_through_unchanged(self):
        view = self.manager.create_location_view(
            location=self.location, name='Kitchen',
        )
        self.assertEqual(view.name, 'Kitchen')

    def test_first_collision_gets_suffix_2(self):
        first = self.manager.create_location_view(
            location=self.location, name='Home Assistant',
        )
        second = self.manager.create_location_view(
            location=self.location, name='Home Assistant',
        )
        self.assertEqual(first.name, 'Home Assistant')
        self.assertEqual(second.name, 'Home Assistant (2)')

    def test_subsequent_collisions_increment_suffix(self):
        self.manager.create_location_view(
            location=self.location, name='Cameras',
        )
        self.manager.create_location_view(
            location=self.location, name='Cameras',
        )
        third = self.manager.create_location_view(
            location=self.location, name='Cameras',
        )
        fourth = self.manager.create_location_view(
            location=self.location, name='Cameras',
        )
        self.assertEqual(third.name, 'Cameras (3)')
        self.assertEqual(fourth.name, 'Cameras (4)')

    def test_collision_isolated_per_location(self):
        """Disambiguation looks at views in the *same* location only;
        a different location with the same view name does not affect
        suffix selection."""
        from hi.apps.location.models import Location
        other_location = Location.objects.create(
            name='Other', svg_view_box_str='0 0 100 100',
        )
        self.manager.create_location_view(
            location=other_location, name='Home Assistant',
        )
        # First call here is unique relative to self.location.
        view = self.manager.create_location_view(
            location=self.location, name='Home Assistant',
        )
        self.assertEqual(view.name, 'Home Assistant')

    def test_skips_taken_suffix_in_sequence(self):
        """Pre-existing '(2)' name still leaves room for an unsuffixed
        first creation, then suffix-2 collision should advance to
        suffix 3."""
        from hi.apps.location.models import LocationView
        # Pre-create a manually-named '(2)' to simulate a deployment
        # where someone already used that exact name.
        LocationView.objects.create(
            location=self.location, name='Lights (2)', order_id=0,
            svg_view_box_str='0 0 100 100', svg_rotate=0,
            svg_style_name_str='COLOR', location_view_type_str='DEFAULT',
        )
        # First 'Lights' creation is unique.
        first = self.manager.create_location_view(
            location=self.location, name='Lights',
        )
        self.assertEqual(first.name, 'Lights')
        # Second collides with both 'Lights' and 'Lights (2)' →
        # advances to (3).
        second = self.manager.create_location_view(
            location=self.location, name='Lights',
        )
        self.assertEqual(second.name, 'Lights (3)')
