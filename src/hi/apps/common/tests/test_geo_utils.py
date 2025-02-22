import logging
import math

from django.test import TestCase

import hi.apps.common.geo_utils as utils

logging.disable(logging.CRITICAL)


class TestGeoDataUtils(TestCase):

    def test_get_distance(self):

        test_data = [
            { 'lat1': 0.0, 'long1': 0.0,
              'lat2': 0.0, 'long2': 1.0,
              'expected': 69.0753543389934,
             },
            { 'lat1': 0.0, 'long1': 0.0,
              'lat2': 0.0, 'long2': -1.0,
              'expected': 69.0753543389934,
             },
            { 'lat1': 0.0, 'long1': 0.0,
              'lat2': 1.0, 'long2': 0.0,
              'expected': 69.0753543389934,
             },
            { 'lat1': 0.0, 'long1': 0.0,
              'lat2': -1.0, 'long2': 0.0,
              'expected': 69.0753543389934,
             },
            { 'lat1': 0.0, 'long1': 0.0,
              'lat2': 1.0, 'long2': 1.0,
              'expected': 97.68482302855615,
             },
            { 'lat1': 0.0, 'long1': 0.0,
              'lat2': -1.0, 'long2': -1.0,
              'expected': 97.68482302855615,
             },
            { 'lat1': 30.0, 'long1': 30.0,
              'lat2': 31.0, 'long2': 31.0,
              'expected': 91.1784601604561,
             },
            { 'lat1': 45.0, 'long1': 45.0,
              'lat2': 55.0, 'long2': 55.0,
              'expected': 819.3611667319492,
             },
            { 'lat1': 10.0, 'long1': 10.0,
              'lat2': 21.0, 'long2': 20.0,
              'expected': 1009.2801682219097,
             },
        ]
    
        for data in test_data:
            result = utils.get_distance( data['lat1'], data['long1'],
                                         data['lat2'], data['long2'], miles = True )
            self.assertAlmostEqual( data['expected'], result, 3, data )
            continue
        return
    
    def test_get_latitude_span(self):
        test_data = [
            { 'distance_miles': 0.0,
              'expected': 0.0,
             },
            { 'distance_miles': 1.0,
              'expected': 0.01440092165898,
             },
            { 'distance_miles': 5.0,
              'expected': 0.072004608294930,
             },
            { 'distance_miles': 500.0,
              'expected': 7.2384717354645165,
             },
            { 'distance_miles': 1000.0,
              'expected':14.476943470929033,
             },
        ]

        for data in test_data:
            result = utils.get_latitude_span( data['distance_miles'] )
            self.assertAlmostEqual( data['expected'], result, 3, data )
            continue
        return

    def test_get_longitude_span(self):
        test_data = [
            { 'latitude': 0.0,
              'distance_miles': 10.0,
              'expected': 0.14476943470929032,
             },
            { 'latitude': 0.0,
              'distance_miles': 0.0,
              'expected': 0.0,
             },
            { 'latitude': 20.0,
              'distance_miles': 10.0,
              'expected': 0.15406064329571237,
             },
            { 'latitude': 40.0,
              'distance_miles': 10.0,
              'expected': 0.1889840664266866,
             },
            { 'latitude': 50.0,
              'distance_miles': 10.0,
              'expected': 0.22522293650156985,
             },
            { 'latitude': -25.0,
              'distance_miles': 10.0,
              'expected': 0.15969426502716177,
             },
        ]

        for data in test_data:
            result = utils.get_longitude_span( data['latitude'], data['distance_miles'] )
            self.assertAlmostEqual( data['expected'], result, 3, data )
            continue
        return
    
    def test_parse_long_lat_from_text__with_usa_bias(self):

        ##########
        # Valid
        
        for text, expect_long, expect_lat in [
                ( 'https://www.google.com/maps/place/Newry,+ME+04261/@44.5074769,-70.8744435,12z/data=!3m1!4b1!4m27!1m21!4m20!1m11!1m2!1s0x4caebe4815802593:0x88e91a6528cad91b!2sBar+Harbor,+Maine!2m2!1d-68.2039123!2d44.3876119!3m4!1m2!1d-68.745781!2d44.7739995!3s0x4cae4cf70901e06d:0x2645e8d4d697b234!1m6!1m2!1s0x5490102c93e83355:0x102565466944d59a!2sSeattle,+Washington!2m2!1d-122.3320708!2d47.6062095!3e0!3m4!1s0x4cb3de91038896f5:0x378c902b5876fa91!8m2!3d44.4884234!4d-70.7886028',
                  -70.8744435, 44.5074769 ),
                ( 'https://www.google.com/maps/place/Mt+Washington/@44.2956246,-71.3783543,9.96z/data=!4m27!1m21!4m20!1m11!1m2!1s0x4caebe4815802593:0x88e91a6528cad91b!2sBar+Harbor,+Maine!2m2!1d-68.2039123!2d44.3876119!3m4!1m2!1d-68.745781!2d44.7739995!3s0x4cae4cf70901e06d:0x2645e8d4d697b234!1m6!1m2!1s0x5490102c93e83355:0x102565466944d59a!2sSeattle,+Washington!2m2!1d-122.3320708!2d47.6062095!3e0!3m4!1s0x4cb38e798f42c3d9:0xc3b88e4dac01db12!8m2!3d44.2707715!4d-71.3033295',
                  -71.3783543, 44.2956246 ),
                ( '\n-71.3783543, 44.295624', -71.3783543, 44.295624 ),
                ( '-71.3783543  44.295624', -71.3783543, 44.295624 ),
                ( '  -71.3783543 / 44.295624  ', -71.3783543, 44.295624 ),
                ( '  -71.3783543 \n\n 44.295624  ', -71.3783543, 44.295624 ),
                ( '  44.295624,-71.3783543 \n\n   ', -71.3783543, 44.295624 ),

                ( '  47.0 -68 \n\n   ', -68.0, 47.0 ),
                ( '  -69.0, 48.0 \n\n   ', -69.0, 48.0 ),

                ( '49.0 N 68 W', -68.0, 49.0 ),
                ( '50N 68.34W', -68.34, 50.0 ),
                ( '40.446° N 79.982° W', -79.982, 40.446 ),
                ( '61° 26.767′ N 79° 58.933′ W', -79.9822167, 61.4461167 ),
                ( '62 26.767N 79 58.933W', -79.9822167, 62.4461167 ),
                ( '40° 26′ 46″ N 79° 58′ 56″ W', -79.982222222, 40.44611111 ),
                ( ' 41°24\'12.2"N 92°10\'26.5"W', -92.174027777778, 41.4033888889 ),
        ]:

            result_lat, result_long = utils.parse_long_lat_from_text( text, usa_biased = True )
            self.assertAlmostEqual( expect_long, result_long, 6, f'Bad longitude for {text}'  )
            self.assertAlmostEqual( expect_lat, result_lat, 6, f'Bad latitude for {text}' )
            continue

        ##########
        # Invalid
        
        for text in [
                'https://www.google.com/maps/place/Newry,+ME+04261/44.5074769,-70.8744435,12z/data=!3m1!4b1!4m27!1m21!4m20!1m11!1m2!1s0x4caebe4815802593:0x88e91a6528cad91b!2sBar+Harbor,+Maine!2m2!1d-68.2039123!2d44.3876119!3m4!1m2!1d-68.745781!2d44.7739995!3s0x4cae4cf70901e06d:0x2645e8d4d697b234!1m6!1m2!1s0x5490102c93e83355:0x102565466944d59a!2sSeattle,+Washington!2m2!1d-122.3320708!2d47.6062095!3e0!3m4!1s0x4cb3de91038896f5:0x378c902b5876fa91!8m2!3d44.4884234!4d-70.7886028'
                '  68.0, -47.0 \n\n   ',
                '47.0 N -68 W',
                '-47.0S 68W',
        ]:
            with self.assertRaises( utils.GeoPointParseError ):
                utils.parse_long_lat_from_text( text, usa_biased = True )
                continue
        return
    
    def test_get_angle_degrees(self):
        test_data = [
            { 'x1': 0.0, 'y1': 0.0,
              'x2': 0.0, 'y2': 0.0,
              'x3': 0.0, 'y3': 0.0,
              'expected': 0.0,
              },
            { 'x1': 0.0, 'y1': 0.0,
              'x2': 1.0, 'y2': 0.0,
              'x3': 0.0, 'y3': 0.0,
              'expected': 0.0,
              },
            { 'x1': 0.0, 'y1': 0.0,
              'x2': 1.0, 'y2': 0.0,
              'x3': 1.0, 'y3': 1.0,
              'expected': 270.0,
              },
            { 'x1': 1.0, 'y1': 0.0,
              'x2': 0.0, 'y2': 0.0,
              'x3': 1.0, 'y3': 1.0,
              'expected': 45.0,
              },
            { 'x1': 1.0, 'y1': 1.0,
              'x2': 0.0, 'y2': 0.0,
              'x3': 1.0, 'y3': 0.0,
              'expected': 315.0,
              },
            { 'x1': 1.0, 'y1': -1.0,
              'x2': 0.0, 'y2': 0.0,
              'x3': 1.0, 'y3': 1.0,
              'expected': 90.0,
              },
            { 'x1': 1.0, 'y1': -1.0,
              'x2': 0.0, 'y2': 0.0,
              'x3': 1.0, 'y3': 0.0,
              'expected': 45.0,
              },
        ]

        for data in test_data:
            result = utils.get_angle_degrees( x1 = data['x1'], y1 = data['y1'],
                                              x2 = data['x2'], y2 = data['y2'],
                                              x3 = data['x3'], y3 = data['y3'] )
            self.assertAlmostEqual( data['expected'], result, 3, data )
            continue
        return
    
    def test_get_distance_to_line(self):
        test_data = [
            { 'line_x1': 0.0, 'line_y1': 0.0,
              'line_x2': 0.0, 'line_y2': 0.0,
              'point_x': 0.0, 'point_y': 0.0,
              'expected': 0.0,
              },
            { 'line_x1': -10.0, 'line_y1': 5.0,
              'line_x2': 20.0, 'line_y2': 5.0,
              'point_x': 0.0, 'point_y': 0.0,
              'expected': 5.0,
              },
            { 'line_x1': 1.0, 'line_y1': 0.0,
              'line_x2': 0.0, 'line_y2': 1.0,
              'point_x': 0.0, 'point_y': 0.0,
              'expected': 1.0 / math.sqrt( 2.0 ),
              },
            { 'line_x1': 0.0, 'line_y1': 2.0,
              'line_x2': -2.0, 'line_y2': 1.0,
              'point_x': 0.0, 'point_y': 0.0,
              'expected': 1.7888,
              },
        ]

        for data in test_data:
            result = utils.get_distance_to_line( line_x1 = data['line_x1'], line_y1 = data['line_y1'],
                                                 line_x2 = data['line_x2'], line_y2 = data['line_y2'],
                                                 point_x = data['point_x'], point_y = data['point_y'] )
            self.assertAlmostEqual( data['expected'], result, 3, data )
            continue
        return
    
    def test_get_point_between_points(self):
        test_data = [
            { 'initial_longitude': 0.0, 'initial_latitude': 0.0,
              'next_longitude': 0.0, 'next_latitude': 0.0,
              'distance_from_initial_miles': 0.0,
              'expected': ( 0.0, 0.0 ),
              },
            { 'initial_longitude': -170.0, 'initial_latitude': 40.0,
              'next_longitude': -171.0, 'next_latitude': 40.0,
              'distance_from_initial_miles': 0.0,
              'expected': ( -170.0, 40.0 ),
              },
            { 'initial_longitude': -170.0, 'initial_latitude': 40.0,
              'next_longitude': -171.0, 'next_latitude': 40.0,
              'distance_from_initial_miles': 53.0,
              'expected': ( -171.0016, 40.0 ),
              },
            { 'initial_longitude': -170.0, 'initial_latitude': 40.0,
              'next_longitude': -170.0, 'next_latitude': 41.0,
              'distance_from_initial_miles': 62.0,
              'expected': ( -170.0, 40.89757 ),
              },
        ]

        for data in test_data:
            result = utils.get_point_between_points(
                initial_longitude = data['initial_longitude'],
                initial_latitude = data['initial_latitude'],
                next_longitude = data['next_longitude'],
                next_latitude = data['next_latitude'],
                distance_from_initial_miles = data['distance_from_initial_miles'],
            )
            self.assertAlmostEqual( data['expected'][0], result[0], 3, data )
            self.assertAlmostEqual( data['expected'][1], result[1], 3, data )
            continue
        return
    
    def test_get_longitude_per_latitude(self):
        test_data = [
            { 'reference_latitude': 0.0,
              'expected': 1.0,
              },
            { 'reference_latitude': 40.0,
              'expected': 1.3054141352847246,
              },
            { 'reference_latitude': 70.0,
              'expected': 2.923837169556057,
              },
        ]

        for data in test_data:
            result = utils.get_longitude_per_latitude( reference_latitude = data['reference_latitude'] )
            self.assertAlmostEqual( data['expected'], result, 3, data )
            continue
        return
    
