import logging

from django.test import TestCase

import waa.apps.common.name_utils as name_utils

logging.disable(logging.CRITICAL)


class TestNameUtils(TestCase):

    def test_RandomNameGenerator(self):

        for _ in range(10):
            self.assertTrue( len(name_utils.RandomNameGenerator.next_first_name()) > 2 )
            self.assertTrue( len(name_utils.RandomNameGenerator.next_last_name()) > 2 )
            self.assertTrue( len(name_utils.RandomNameGenerator.next_full_name()) > 2 )
            continue
        return
    
