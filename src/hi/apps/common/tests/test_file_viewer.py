import logging

from django.test import SimpleTestCase

from hi.apps.common.file_viewer import FileViewerKind, file_viewer_attrs

logging.disable( logging.CRITICAL )


class TestFileViewerKindFromMimeType( SimpleTestCase ):

    def test_mime_types_map_to_kinds( self ):
        expected_kinds = {
            'image/jpeg': FileViewerKind.IMAGE,
            'image/svg+xml': FileViewerKind.IMAGE,
            'application/pdf': FileViewerKind.PDF,
            'video/mp4': FileViewerKind.VIDEO,
            'audio/mpeg': FileViewerKind.AUDIO,
            'text/plain': FileViewerKind.TEXT,
            'text/csv': FileViewerKind.TEXT,
            'application/zip': FileViewerKind.UNSUPPORTED,
            'application/pdfx': FileViewerKind.UNSUPPORTED,
            'imagery': FileViewerKind.UNSUPPORTED,
        }
        for mime_type, expected_kind in expected_kinds.items():
            with self.subTest( mime_type = mime_type ):
                self.assertIs( FileViewerKind.from_mime_type( mime_type ), expected_kind )
            continue
        return

    def test_mime_type_case_and_whitespace_are_ignored( self ):
        self.assertIs( FileViewerKind.from_mime_type( ' Application/PDF ' ), FileViewerKind.PDF )
        self.assertIs( FileViewerKind.from_mime_type( 'IMAGE/PNG' ), FileViewerKind.IMAGE )
        return

    def test_missing_mime_type_is_unsupported( self ):
        self.assertIs( FileViewerKind.from_mime_type( None ), FileViewerKind.UNSUPPORTED )
        self.assertIs( FileViewerKind.from_mime_type( '' ), FileViewerKind.UNSUPPORTED )
        return


class TestFileViewerAttrs( SimpleTestCase ):

    def test_all_details_rendered( self ):
        markup = file_viewer_attrs(
            url = '/media/manual.pdf',
            mime_type = 'application/pdf',
            title = 'Manual',
            filename = 'manual.pdf',
            size_bytes = 2048,
        )
        self.assertEqual(
            markup,
            'data-file-viewer-url="/media/manual.pdf" data-file-viewer-kind="pdf"'
            ' data-file-viewer-title="Manual" data-file-viewer-filename="manual.pdf"'
            ' data-file-viewer-mime-type="application/pdf" data-file-viewer-size="2.0\xa0KB"',
        )
        return

    def test_unknown_details_omitted_and_title_falls_back_to_filename( self ):
        only_url = file_viewer_attrs( url = '/proxy/1' )
        self.assertEqual(
            only_url,
            'data-file-viewer-url="/proxy/1" data-file-viewer-kind="unsupported"',
        )
        untitled = file_viewer_attrs( url = '/media/a.png', filename = 'a.png' )
        self.assertIn( 'data-file-viewer-title="a.png"', untitled )
        return

    def test_zero_byte_size_is_shown( self ):
        markup = file_viewer_attrs( url = '/media/empty.txt', size_bytes = 0 )
        self.assertIn( 'data-file-viewer-size="0\xa0bytes"', markup )
        return

    def test_values_are_escaped( self ):
        markup = file_viewer_attrs( url = '/media/a.png', title = '"><script>' )
        self.assertIn( 'data-file-viewer-title="&quot;&gt;&lt;script&gt;"', markup )
        return

    def test_missing_url_fails( self ):
        with self.assertRaises( ValueError ):
            file_viewer_attrs( url = '' )
        return
