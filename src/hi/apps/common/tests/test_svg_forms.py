import logging

from django.core.files.uploadedfile import SimpleUploadedFile

from hi.apps.common.svg_forms import SvgFileForm
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSvgFileForm(SvgFileForm):
    """Concrete subclass of SvgFileForm for testing purposes."""

    def allow_default_svg_file(self):
        return False

    def get_media_destination_directory(self):
        return 'test/svg'


def _make_svg_with_element(inner_element):
    """Build a minimal valid SVG string wrapping the given inner element."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'{inner_element}'
        '</svg>'
    )


def _make_upload(svg_string, filename='test.svg'):
    """Wrap SVG string content into a SimpleUploadedFile."""
    return SimpleUploadedFile(
        name=filename,
        content=svg_string.encode('utf-8'),
        content_type='image/svg+xml',
    )


class TestSvgFileFormHrefHandling(BaseTestCase):
    """
    Tests for SvgFileForm.clean() handling of href and xlink:href attributes.

    Internal fragment references (starting with '#') should be preserved.
    External URLs should be removed and counted as dangerous.
    """

    def _submit_form(self, svg_content, remove_dangerous=True):
        """
        Submit SVG content through the form and return (form, is_valid).

        When remove_dangerous is True, the form will strip dangerous items
        and return cleaned content. When False, the form will flag dangerous
        items but not strip them (requires a second submission).
        """
        svg_file = _make_upload(svg_content)
        data = {
            'has_dangerous_svg_items': 'false',
        }
        if remove_dangerous:
            data['remove_dangerous_svg_items'] = 'on'
            data['has_dangerous_svg_items'] = 'true'

        files = {'svg_file': svg_file}
        form = TestSvgFileForm(data=data, files=files)
        return form, form.is_valid()

    def test_internal_href_is_preserved(self):
        """An href starting with '#' should remain in the cleaned SVG content."""
        svg = _make_svg_with_element('<a href="#section1"><rect width="10" height="10"/></a>')
        form, is_valid = self._submit_form(svg)

        self.assertTrue(is_valid)
        fragment_content = form.cleaned_data['svg_fragment_content']
        self.assertIn('href="#section1"', fragment_content)

    def test_external_href_is_removed_when_dangerous_items_accepted(self):
        """An href with an external URL should be stripped from cleaned content."""
        svg = _make_svg_with_element('<a href="http://evil.com"><rect width="10" height="10"/></a>')
        form, is_valid = self._submit_form(svg, remove_dangerous=True)

        self.assertTrue(is_valid)
        fragment_content = form.cleaned_data['svg_fragment_content']
        self.assertNotIn('http://evil.com', fragment_content)
        self.assertNotIn('href=', fragment_content)

    def test_external_href_is_flagged_as_dangerous(self):
        """An href with external URL should be counted as a dangerous attribute."""
        svg = _make_svg_with_element('<a href="http://evil.com"><rect width="10" height="10"/></a>')
        form, is_valid = self._submit_form(svg, remove_dangerous=False)

        # Form should be invalid because dangerous items were found but not approved
        self.assertFalse(is_valid)
        # The dangerous attr count should include href
        self.assertIn('href', form._dangerous_attr_counts)
        self.assertEqual(form._dangerous_attr_counts['href'], 1)

    def test_xlink_href_internal_is_preserved(self):
        """An xlink:href starting with '#' should remain in cleaned SVG content."""
        svg = _make_svg_with_element(
            '<use xlink:href="#my-symbol" xmlns:xlink="http://www.w3.org/1999/xlink"/>'
        )
        form, is_valid = self._submit_form(svg)

        self.assertTrue(is_valid)
        fragment_content = form.cleaned_data['svg_fragment_content']
        # The attribute value should reference the internal fragment
        self.assertIn('#my-symbol', fragment_content)

    def test_xlink_href_external_is_removed(self):
        """External xlink:href URLs should be removed as dangerous."""
        svg = _make_svg_with_element(
            '<use xlink:href="http://evil.com/sprite.svg#icon"'
            ' xmlns:xlink="http://www.w3.org/1999/xlink"/>'
        )
        form, is_valid = self._submit_form(svg, remove_dangerous=True)

        self.assertTrue(is_valid)
        fragment_content = form.cleaned_data['svg_fragment_content']
        self.assertNotIn('evil.com', fragment_content)

    def test_onclick_event_handler_is_flagged(self):
        """Event handler attributes like onclick should be removed."""
        svg = _make_svg_with_element('<rect width="10" height="10" onclick="alert(1)"/>')
        form, is_valid = self._submit_form(svg, remove_dangerous=True)

        self.assertTrue(is_valid)
        fragment_content = form.cleaned_data['svg_fragment_content']
        self.assertNotIn('onclick', fragment_content)
        self.assertNotIn('alert', fragment_content)

    def test_onclick_is_counted_as_dangerous(self):
        """onclick should appear in the dangerous attribute counts."""
        svg = _make_svg_with_element('<rect width="10" height="10" onclick="alert(1)"/>')
        form, is_valid = self._submit_form(svg, remove_dangerous=False)

        self.assertFalse(is_valid)
        self.assertIn('onclick', form._dangerous_attr_counts)
        self.assertEqual(form._dangerous_attr_counts['onclick'], 1)

    def test_onload_event_handler_is_flagged(self):
        """onload event handler should be removed from cleaned content."""
        svg = _make_svg_with_element('<rect width="10" height="10" onload="init()"/>')
        form, is_valid = self._submit_form(svg, remove_dangerous=True)

        self.assertTrue(is_valid)
        fragment_content = form.cleaned_data['svg_fragment_content']
        self.assertNotIn('onload', fragment_content)

    def test_onmouseover_event_handler_is_flagged(self):
        """onmouseover event handler should be removed from cleaned content."""
        svg = _make_svg_with_element('<rect width="10" height="10" onmouseover="highlight()"/>')
        form, is_valid = self._submit_form(svg, remove_dangerous=True)

        self.assertTrue(is_valid)
        fragment_content = form.cleaned_data['svg_fragment_content']
        self.assertNotIn('onmouseover', fragment_content)

    def test_multiple_dangerous_attrs_are_all_counted(self):
        """Multiple dangerous attributes across elements should all be counted."""
        svg = _make_svg_with_element(
            '<rect width="10" height="10" onclick="a()" onload="b()"/>'
            '<circle r="5" onmouseover="c()"/>'
        )
        form, is_valid = self._submit_form(svg, remove_dangerous=False)

        self.assertFalse(is_valid)
        self.assertIn('onclick', form._dangerous_attr_counts)
        self.assertIn('onload', form._dangerous_attr_counts)
        self.assertIn('onmouseover', form._dangerous_attr_counts)

    def test_safe_attributes_are_preserved(self):
        """Normal SVG attributes like fill, stroke should not be affected."""
        svg = _make_svg_with_element(
            '<rect width="10" height="10" fill="blue" stroke="red" stroke-width="2"/>'
        )
        form, is_valid = self._submit_form(svg)

        self.assertTrue(is_valid)
        fragment_content = form.cleaned_data['svg_fragment_content']
        self.assertIn('fill="blue"', fragment_content)
        self.assertIn('stroke="red"', fragment_content)

    def test_dangerous_tags_are_removed(self):
        """Dangerous tags like <script> should be removed from cleaned content."""
        svg = _make_svg_with_element(
            '<rect width="10" height="10"/>'
            '<script>alert("xss")</script>'
        )
        form, is_valid = self._submit_form(svg, remove_dangerous=True)

        self.assertTrue(is_valid)
        fragment_content = form.cleaned_data['svg_fragment_content']
        self.assertNotIn('script', fragment_content)
        self.assertNotIn('alert', fragment_content)

    def test_viewbox_is_extracted(self):
        """The SVG viewBox should be parsed and available in cleaned_data."""
        svg = _make_svg_with_element('<rect width="10" height="10"/>')
        form, is_valid = self._submit_form(svg)

        self.assertTrue(is_valid)
        svg_viewbox = form.cleaned_data['svg_viewbox']
        self.assertEqual(svg_viewbox.x, 0)
        self.assertEqual(svg_viewbox.y, 0)
        self.assertEqual(svg_viewbox.width, 100)
        self.assertEqual(svg_viewbox.height, 100)

    def test_missing_svg_file_raises_validation_error(self):
        """Submitting with no file and allow_default=False should fail validation."""
        data = {'has_dangerous_svg_items': 'false'}
        form = TestSvgFileForm(data=data, files={})
        self.assertFalse(form.is_valid())
