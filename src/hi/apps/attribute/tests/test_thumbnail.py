"""Tests for ThumbnailHelpers.bytes_to_thumbnail_png.

Generates source bytes inline with Pillow (the same library the
helper consumes) so test fixtures stay self-contained and the
asserts cover real PNG/JPEG round-trips, not stub data.
"""
import logging
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase
from PIL import Image

from hi.apps.attribute.thumbnail import ThumbnailHelpers


logging.disable(logging.CRITICAL)


def _make_image_bytes(format='PNG', size=(640, 480), color='red'):
    img = Image.new('RGB', size, color)
    buf = BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


class TestBytesToThumbnailPng(SimpleTestCase):

    def test_jpeg_in_returns_png_under_thumbnail_size(self):
        src = _make_image_bytes(format='JPEG', size=(800, 600))
        out = ThumbnailHelpers.bytes_to_thumbnail_png(src, 'image/jpeg')
        self.assertIsNotNone(out)
        with Image.open(BytesIO(out)) as img:
            self.assertEqual(img.format, 'PNG')
            self.assertLessEqual(img.width, ThumbnailHelpers.THUMBNAIL_SIZE[0])
            self.assertLessEqual(img.height, ThumbnailHelpers.THUMBNAIL_SIZE[1])

    def test_png_in_returns_png(self):
        src = _make_image_bytes(format='PNG', size=(400, 300))
        out = ThumbnailHelpers.bytes_to_thumbnail_png(src, 'image/png')
        self.assertIsNotNone(out)
        with Image.open(BytesIO(out)) as img:
            self.assertEqual(img.format, 'PNG')

    def test_mime_type_with_charset_suffix_is_accepted(self):
        # Some upstreams return "image/jpeg; charset=binary" or similar
        # -- the leading mime type is what matters.
        src = _make_image_bytes(format='JPEG')
        out = ThumbnailHelpers.bytes_to_thumbnail_png(
            src, 'image/jpeg; charset=binary',
        )
        self.assertIsNotNone(out)

    def test_empty_bytes_returns_none(self):
        self.assertIsNone(
            ThumbnailHelpers.bytes_to_thumbnail_png(b'', 'image/png')
        )

    def test_unsupported_mime_type_returns_none(self):
        src = _make_image_bytes(format='PNG')
        self.assertIsNone(
            ThumbnailHelpers.bytes_to_thumbnail_png(src, 'text/plain')
        )

    def test_empty_mime_type_returns_none(self):
        src = _make_image_bytes(format='PNG')
        self.assertIsNone(ThumbnailHelpers.bytes_to_thumbnail_png(src, ''))

    def test_oversize_image_returns_none(self):
        # Synthesize a byte string that exceeds the image cap without
        # actually allocating that much pixel data -- the size check
        # runs against len(source_bytes), not decoded image dimensions.
        oversize = b'x' * (ThumbnailHelpers.MAX_SOURCE_BYTES + 1)
        self.assertIsNone(
            ThumbnailHelpers.bytes_to_thumbnail_png(oversize, 'image/jpeg')
        )

    def test_oversize_pdf_returns_none(self):
        oversize = b'x' * (ThumbnailHelpers.MAX_PDF_SOURCE_BYTES + 1)
        self.assertIsNone(
            ThumbnailHelpers.bytes_to_thumbnail_png(
                oversize, 'application/pdf',
            )
        )

    def test_malformed_image_bytes_returns_none(self):
        self.assertIsNone(
            ThumbnailHelpers.bytes_to_thumbnail_png(b'not an image', 'image/png')
        )

    @patch('pdf2image.convert_from_bytes')
    def test_pdf_dispatch_calls_pdf2image(self, mock_convert):
        # Verify the PDF branch routes through pdf2image. Return a
        # real PIL image so the downstream PIL save path still works.
        mock_convert.return_value = [Image.new('RGB', (640, 480), 'blue')]
        out = ThumbnailHelpers.bytes_to_thumbnail_png(
            b'%PDF-1.4 stub', 'application/pdf',
        )
        self.assertIsNotNone(out)
        mock_convert.assert_called_once()

    @patch('pdf2image.convert_from_bytes', return_value=[])
    def test_pdf_with_no_pages_returns_none(self, _mock_convert):
        self.assertIsNone(
            ThumbnailHelpers.bytes_to_thumbnail_png(
                b'%PDF-1.4 stub', 'application/pdf',
            )
        )

    @patch('pdf2image.convert_from_bytes', side_effect=RuntimeError('boom'))
    def test_pdf_render_exception_returns_none(self, _mock_convert):
        self.assertIsNone(
            ThumbnailHelpers.bytes_to_thumbnail_png(
                b'%PDF-1.4 stub', 'application/pdf',
            )
        )
