import logging

from django.test import TestCase

import waa.apps.common.email_utils as email_utils

logging.disable(logging.CRITICAL)


class EmailUtilsTestCase(TestCase):

    def test_parse_emails_from_text(self):

        text = """
        foo
        bar
        biz, bif  , baz
        foo1@example.com

        foo2@example.com, foo3@example.com  ;  foo4@example.com
 
        """

        expected = [
            'foo',
            'bar',
            'biz',
            'bif',
            'baz',
            'foo1@example.com',
            'foo2@example.com',
            'foo3@example.com',
            'foo4@example.com',
        ]

        result = email_utils.parse_emails_from_text( text )
        self.assertEqual( expected, result )
        return
    
    
