import logging
import re

from django.template.defaultfilters import filesizeformat
from django.test import SimpleTestCase

from hi.apps.common.file_viewer import FileViewerItem, FileViewerKind, file_viewer_attrs
from hi.constants import DIVID

logging.disable( logging.CRITICAL )


class TestFileViewerKindFromMimeType( SimpleTestCase ):

    def test_only_browser_displayable_formats_are_viewable( self ):
        expected_kinds = {
            'application/pdf': FileViewerKind.PDF,
            'image/jpeg': FileViewerKind.IMAGE,
            'image/heic': FileViewerKind.UNSUPPORTED,
            'image/tiff': FileViewerKind.UNSUPPORTED,
            'video/quicktime': FileViewerKind.UNSUPPORTED,
            'application/zip': FileViewerKind.UNSUPPORTED,
            'application/pdfx': FileViewerKind.UNSUPPORTED,
        }
        for mime_type, expected_kind in expected_kinds.items():
            with self.subTest( mime_type = mime_type ):
                self.assertIs( FileViewerKind.from_mime_type( mime_type ), expected_kind )
            continue
        return

    def test_any_text_type_and_structured_text_read_as_text( self ):
        for mime_type in ( 'text/plain', 'text/csv', 'application/json' ):
            with self.subTest( mime_type = mime_type ):
                self.assertIs( FileViewerKind.from_mime_type( mime_type ), FileViewerKind.TEXT )
            continue
        self.assertIs( FileViewerKind.from_mime_type( 'textual/plain' ), FileViewerKind.UNSUPPORTED )
        return

    def test_mime_type_case_whitespace_and_parameters_are_ignored( self ):
        self.assertIs( FileViewerKind.from_mime_type( ' Application/PDF ' ), FileViewerKind.PDF )
        self.assertIs( FileViewerKind.from_mime_type( 'IMAGE/PNG' ), FileViewerKind.IMAGE )
        self.assertIs( FileViewerKind.from_mime_type( 'application/pdf; name=x.pdf' ), FileViewerKind.PDF )
        return

    def test_missing_mime_type_is_unsupported( self ):
        self.assertIs( FileViewerKind.from_mime_type( None ), FileViewerKind.UNSUPPORTED )
        self.assertIs( FileViewerKind.from_mime_type( '' ), FileViewerKind.UNSUPPORTED )
        return


class TestFileViewerAttrs( SimpleTestCase ):

    def parse( self, markup : str ) -> dict:
        return dict( re.findall( r'(\S+)="([^"]*)"', markup ))

    def test_all_details_rendered( self ):
        attrs = self.parse( file_viewer_attrs( FileViewerItem(
            url = '/media/manual.pdf',
            mime_type = 'application/pdf',
            title = 'Manual',
            filename = 'manual.pdf',
            size_bytes = 2048,
        )))
        self.assertEqual( attrs[ DIVID['FILE_VIEWER_URL_ATTR'] ], '/media/manual.pdf' )
        self.assertEqual( attrs[ DIVID['FILE_VIEWER_KIND_ATTR'] ], FileViewerKind.PDF.external_name )
        self.assertEqual( attrs[ DIVID['FILE_VIEWER_TITLE_ATTR'] ], 'Manual' )
        self.assertEqual( attrs[ DIVID['FILE_VIEWER_FILENAME_ATTR'] ], 'manual.pdf' )
        self.assertEqual( attrs[ DIVID['FILE_VIEWER_MIME_TYPE_ATTR'] ], 'application/pdf' )
        self.assertEqual( attrs[ DIVID['FILE_VIEWER_SIZE_ATTR'] ], filesizeformat( 2048 ))
        return

    def test_unknown_details_omitted_and_title_falls_back_to_filename( self ):
        only_url = self.parse( file_viewer_attrs( FileViewerItem( url = '/proxy/1' )))
        self.assertEqual(
            set( only_url ),
            { DIVID['FILE_VIEWER_URL_ATTR'], DIVID['FILE_VIEWER_KIND_ATTR'] },
        )
        self.assertEqual( only_url[ DIVID['FILE_VIEWER_KIND_ATTR'] ], FileViewerKind.UNSUPPORTED.external_name )

        untitled = self.parse( file_viewer_attrs( FileViewerItem( url = '/media/a.png', filename = 'a.png' )))
        self.assertEqual( untitled[ DIVID['FILE_VIEWER_TITLE_ATTR'] ], 'a.png' )
        return

    def test_zero_byte_size_is_shown( self ):
        attrs = self.parse( file_viewer_attrs( FileViewerItem( url = '/media/empty.txt', size_bytes = 0 )))
        self.assertEqual( attrs[ DIVID['FILE_VIEWER_SIZE_ATTR'] ], filesizeformat( 0 ))
        return

    def test_values_are_escaped( self ):
        markup = file_viewer_attrs( FileViewerItem( url = '/media/a.png', title = '"><script>' ))
        self.assertNotIn( '<script>', markup )
        self.assertEqual( self.parse( markup )[ DIVID['FILE_VIEWER_TITLE_ATTR'] ], '&quot;&gt;&lt;script&gt;' )
        return

    def test_missing_item_disables_the_trigger( self ):
        self.assertEqual( file_viewer_attrs( None ), 'disabled' )
        return

    def test_item_without_url_fails( self ):
        with self.assertRaises( ValueError ):
            file_viewer_attrs( FileViewerItem( url = '' ))
        return
