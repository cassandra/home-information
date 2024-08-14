import logging

from django.test import TestCase

from waa.apps.common.url_utils import simplify_url_path

logging.disable(logging.CRITICAL)


class UrlUtilsTestCase(TestCase):

    def test_simplify_url_path(self):
        test_data_list = [
            ( '/', '/' ),
            ( '/contact', '/contact' ),
            ( '/help', '/help' ),
            ( '/privacy', '/privacy' ),
            ( '/tos', '/tos' ),
            ( '/accounts/login/', '/accounts/login/' ),
            ( '/accounts/google/login/', '/accounts/google/login/' ),
            ( '/accounts/facebook/login/', '/accounts/facebook/login/' ),
            ( '/accounts/google/login/callback/', '/accounts/google/login/callback/' ),
            ( '/accounts/facebook/login/callback/', '/accounts/facebook/login/callback/' ),
            ( '/accounts/social/signup/', '/accounts/social/signup/' ),
            ( '/accounts/logout/', '/accounts/logout/' ),
            ( '/accounts/password/reset/', '/accounts/password/reset/' ),
            ( '/accounts/password/reset/done/', '/accounts/password/reset/done/' ),
            ( '/accounts/signup/', '/accounts/signup/' ),
            ( '/api/user/info/sadfasdfasdfasdfasdf', '/api/user/info' ),
            ( '/img/avatar/sm/fun_car/ffddee.png', '/img/avatar' ),
            ( '/img/map/usa/visited-HI-DE/active-DE/400.png', '/img/map/usa' ),
            ( '/img/map/region/ny.png', '/img/map/region' ),
            ( '/img/award/icon/lg/bronze.png', '/img/award' ),
            ( '/img/award/trophy/lg/silver.png', '/img/award' ),
            ( '/img/badge/sm/daily_top_score/4/345.png', '/img/badge' ),
            ( '/img/location/lg/dam.png', '/img/location' ),
            
        ]

        for path, expected in test_data_list:
            result = simplify_url_path( original_path = path )
            self.assertEqual( expected, result, path )
            continue
        return
