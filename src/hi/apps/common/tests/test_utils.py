import logging

from django.contrib.auth import get_user_model
from django.test import TestCase

import waa.apps.common.utils as utils

logging.disable(logging.CRITICAL)


class CommonUtilsTestCase(TestCase):

    def setUp(self):
        self.User = get_user_model()
        return
    
    def test_get_long_display_name(self):

        test_data = [
            { 'user': self.User.objects.create_user( first_name = 'Sampling',
                                                     last_name = 'Pampling',
                                                     email = 'sample1@example.com',
                                                     password = 'top_secret' ),
              'expected': 'Pampling, Sampling',
              },
            { 'user': self.User.objects.create_user( last_name = 'Pampling',
                                                     email = 'sample2@example.com',
                                                     password = 'top_secret' ),
              'expected': 'Pampling',
              },
            { 'user': self.User.objects.create_user( first_name = 'Sampling',
                                                     email = 'sample3@example.com',
                                                     password = 'top_secret' ),
              'expected': 'Sampling',
              },
            { 'user': self.User.objects.create_user( email = 'sample4@example.com',
                                                     password = 'top_secret' ),
              'expected': 'sample4',
              },
        ]

        for data in test_data:
            result = utils.get_long_display_name( data['user'] )
            self.assertEqual( data['expected'], result )
            continue
        return
        
    def test_get_short_display_name(self):

        test_data = [
            { 'user': self.User.objects.create_user( first_name = 'Sampling',
                                                     last_name = 'Pampling',
                                                     email = 'sample1@example.com',
                                                     password = 'top_secret' ),
              'expected': 'Sampling',
              },
            { 'user': self.User.objects.create_user( last_name = 'Pampling',
                                                     email = 'sample2@example.com',
                                                     password = 'top_secret' ),
              'expected': 'Pampling',
              },
            { 'user': self.User.objects.create_user( first_name = 'Sampling',
                                                     email = 'sample3@example.com',
                                                     password = 'top_secret' ),
              'expected': 'Sampling',
              },
            { 'user': self.User.objects.create_user( email = 'sample4@example.com',
                                                     password = 'top_secret' ),
              'expected': 'sample4',
              },
        ]

        for data in test_data:
            result = utils.get_short_display_name( data['user'] )
            self.assertEqual( data['expected'], result )
            continue
        return

    def test_get_humanized_secs(self):

        data_list = [
            { 'secs': 0,
              'expect': '0 secs',
            },
            { 'secs': 1,
              'expect': '1 sec',
            },
            { 'secs': 2,
              'expect': '2 secs',
            },
            { 'secs': 59,
              'expect': '59 secs',
            },
            { 'secs': 60,
              'expect': '1 min',
            },
            { 'secs': 61,
              'expect': '1 min, 1 sec',
            },
            { 'secs': 65,
              'expect': '1 min, 5 secs',
            },
            { 'secs': 120,
              'expect': '2 mins',
            },
            { 'secs': 121,
              'expect': '2 mins, 1 sec',
            },
            { 'secs': 126,
              'expect': '2 mins, 6 secs',
            },
            { 'secs': 60 * 60 - 1,
              'expect': '59 mins, 59 secs',
            },
            { 'secs': 60 * 60,
              'expect': '1 hr',
            },
            { 'secs': 60 * 60 + 1,
              'expect': '1 hr, 1 sec',
            },
            { 'secs': 60 * 60 + 24,
              'expect': '1 hr, 24 secs',
            },
            { 'secs': 60 * 60 + 61,
              'expect': '1 hr, 1 min, 1 sec',
            },
            { 'secs': 60 * 60 + 68,
              'expect': '1 hr, 1 min, 8 secs',
            },
            { 'secs': 60 * 60 + 120,
              'expect': '1 hr, 2 mins',
            },
            { 'secs': 60 * 60 + 121,
              'expect': '1 hr, 2 mins, 1 sec',
            },
            { 'secs': 60 * 60 + 127,
              'expect': '1 hr, 2 mins, 7 secs',
            },
            { 'secs': 2 * 60 * 60 + 127,
              'expect': '2 hrs, 2 mins, 7 secs',
            },
            { 'secs': 24 * 60 * 60 + 1,
              'expect': '1 day, 1 sec',
            },
            { 'secs': 24 * 60 * 60 + 11,
              'expect': '1 day, 11 secs',
            },
            { 'secs': 24 * 60 * 60 + 60,
              'expect': '1 day, 1 min',
            },
            { 'secs': 24 * 60 * 60 + 3669,
              'expect': '1 day, 1 hr, 1 min, 9 secs',
            },
        ]

        for data in data_list:
            self.assertEqual( data['expect'], utils.get_humanized_secs( data['secs'] ), data )
            continue
        return
    
    def test_get_humanized_number(self):

        data_list = [
            ( 0, 'zero' ),
            ( 1, '1st' ),
            ( 2, '2nd' ),
            ( 3, '3rd' ),
            ( 4, '4th' ),
            ( 5, '5th' ),
            ( 6, '6th' ),
            ( 7, '7th' ),
            ( 8, '8th' ),
            ( 9, '9th' ),
            ( 10, '10th' ),
            ( 11, '11th' ),
            ( 12, '12th' ),
            ( 13, '13th' ),
            ( 14, '14th' ),
            ( 15, '15th' ),
            ( 16, '16th' ),
            ( 17, '17th' ),
            ( 18, '18th' ),
            ( 19, '19th' ),
            ( 20, '20th' ),
            ( 21, '21st' ),
            ( 22, '22nd' ),
            ( 23, '23rd' ),
            ( 24, '24th' ),
            ( 25, '25th' ),
            ( 30, '30th' ),
            ( 31, '31st' ),
            ( 42, '42nd' ),
            ( 53, '53rd' ),
            ( 64, '64th' ),
            ( 101, '101st' ),
            ( 111, '111th' ),
            ( 1025, '1,025th' ),
            ( 10002, '10,002nd' ),
            ( 10012, '10,012th' ),
        ]

        for value, expected_result in data_list:
            self.assertEqual( expected_result, utils.get_humanized_number(value), f'{value}' )
            continue
        return
    
    def test_is_profanity_text(self):

        data_list = [
            ( 'Normal sentence', False ),
            ( 'Normal', False ),
            ( 'tofu ckicken', False ),
            ( 'fuck', True ),
            ( 'fucks', True ),
            ( 'shit', True ),
            ( 'ass', True ),
            ( 'i cannot say fuck?', True ),
            ( 'fuck.this', True ),
        ]

        for text, expected_result in data_list:
            self.assertEqual( expected_result, utils.is_profanity_text(text), f'{text}' )
            continue
        return
    
    def test_url_simplify(self):

        data_list = [
            ( None, '' ),
            ( '     ', '' ),
            ( '--,.<>!@#$%^&*(_+=', '_' ),
            ( 'foo', 'foo' ),
            ( 'Foo Bar', 'foo-bar' ),
            ( '   Foo, Bar!  ', 'foo-bar' ),
        ]

        for data in data_list:
            self.assertEqual( data[1], utils.url_simplify( data[0] ), data )
            continue
        return
    
    def test_hash_with_seed(self):

        # This guards against changing the seed value. Do not change the seed value.
        
        self.assertEqual( '2e6451b4d14aded1fba1d30dcc780a04265238a4fa4813c1e69bc931344cd3b6',
                          utils.hash_with_seed( value = None ) )
        self.assertEqual( 'e8a59d67adb70cccff3b36bb5a079d5b2519e4013ec3d02548446a099a66d7a1',
                          utils.hash_with_seed( value = 'foo@example.com' ) )
        return
    
    def test_get_url_top_level_domain(self):

        data_list = [
            ( None, None ),
            ( '', None ),
            ( '     ', None ),
            ( '--,.<>!@#$%^&*(_+=', None ),
            ( 'foo', None ),
            ( 'foo/bar', None ),
            ( '/foo/bar', None ),
            ( 'http://foo/bar', None ),
            ( 'https://foo.com/bar', 'foo.com' ),
            ( 'https://no.foo.com/bar', 'foo.com' ),
            ( 'https://no.yes.foo.com/bar', 'foo.com' ),
        ]

        for data in data_list:
            self.assertEqual( data[1], utils.get_url_top_level_domain( data[0] ), data )
            continue
        return
    
    def test_jaccard_coefficient(self):
        test_data_list = [
            { 'tuple_1': ( 0, 0 ), 'tuple_2': ( 0, 0 ), 'expect': 1.0 },
            { 'tuple_1': ( 0, 0 ), 'tuple_2': ( 1, 1 ), 'expect': 0.0 },
            { 'tuple_1': ( 1, 1 ), 'tuple_2': ( 1, 1 ), 'expect': 1.0 },
            { 'tuple_1': ( 1, 1 ), 'tuple_2': ( 0, 0 ), 'expect': 0.0 },
            { 'tuple_1': ( 0, 1 ), 'tuple_2': ( 0, 0 ), 'expect': 0.0 },
            { 'tuple_1': ( 0, 1 ), 'tuple_2': ( 1, 1 ), 'expect': 0.0 },
            { 'tuple_1': ( 0, 2 ), 'tuple_2': ( 0, 1 ), 'expect': 0.5 },
            { 'tuple_1': ( 0, 2 ), 'tuple_2': ( 0, 2 ), 'expect': 1.0 },
            { 'tuple_1': ( 0, 2 ), 'tuple_2': ( 0, 10 ), 'expect': 0.2 },
        ]

        for test_data in test_data_list:
            result = utils.jaccard_coefficient( test_data['tuple_1'], test_data['tuple_2'] )
            self.assertAlmostEqual( test_data['expect'], result, 6, test_data )
            continue
        return
    
