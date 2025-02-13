import logging

from django.test import TestCase

from hi.apps.common.url_utils import simplify_url_path

logging.disable(logging.CRITICAL)


class UrlUtilsTestCase(TestCase):

    def test_simplify_url_path(self):
        test_data_list = [
            ( '/', '/' ),
            ( '/contact', '/contact' ),
            ( '/help', '/help' ),
            ( '/privacy', '/privacy' ),
            ( '/tos', '/tos' ),
            
        ]

        for path, expected in test_data_list:
            result = simplify_url_path( original_path = path )
            self.assertEqual( expected, result, path )
            continue
        return
