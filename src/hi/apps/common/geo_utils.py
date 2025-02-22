import difflib
import math
import re


class GeoPointParseError( ValueError ):
    pass


MILES_PER_KM = 0.621371

EARTH_RADIUS_AT_EQUATOR_KM = 6378.137
EARTH_RADIUS_AT_POLES_KM = 6356.752
EARTH_RADIUS_AT_LAT_25_KM = 6374.344
EARTH_RADIUS_AT_LAT_40_KM = 6369.345
EARTH_RADIUS_AT_LAT_49_KM = 6366.001

EARTH_RADIUS_AT_EQUATOR_MILES = EARTH_RADIUS_AT_EQUATOR_KM * MILES_PER_KM
EARTH_RADIUS_AT_LAT_40_MILES = EARTH_RADIUS_AT_LAT_40_KM * MILES_PER_KM

# For each line of latitude (would be independent of
# location on globe if the earth was a perfect sphere).
#
# OLD MILES_PER_LATITUDE_LINE = 69.44
# NEW MILES_PER_LATITUDE_LINE = 69.0753543389934 (now calculated form radius)
#
MILES_PER_LATITUDE_LINE = 2.0 * math.pi * EARTH_RADIUS_AT_LAT_40_MILES / 360.0
MILES_PER_LONGITUDE_LINE_AT_LAT_40 = 53.00


def get_distance( lat1 : float, lng1 : float, lat2 : float, lng2 : float, miles=True ):
    """ 
    Distance between two lat/lng coordinates in km using the Haversine formula.
    Uses decimal degrees.

    Copyright 2016, Chris Youderian, SimpleMaps, http://simplemaps.com/resources/location-distance
    Released under MIT license - https://opensource.org/licenses/MIT
    """
    earth_radius = EARTH_RADIUS_AT_LAT_40_KM
    
    lat1 = math.radians( lat1 )
    lat2 = math.radians( lat2 )
    lat_dif = lat2 - lat1
    lng_dif = math.radians( lng2 - lng1 )
    a = math.sin( lat_dif / 2.0 )**2 + math.cos( lat1 ) * math.cos( lat2 ) * math.sin( lng_dif / 2.0 )**2
    distance_km = 2 * earth_radius * math.asin( math.sqrt(a) )

    if miles:
        return distance_km * MILES_PER_KM
    else:
        return distance_km

    
def get_angle_degrees( x1, y1, x2, y2, x3, y3 ):
    ang = math.degrees( math.atan2( y3 - y2, x3 - x2 )
                        - math.atan2( y1 - y2, x1 - x2 ))
    return ang + 360 if ang < 0 else ang


def get_distance_to_line( line_x1, line_y1, line_x2, line_y2, point_x, point_y ):

    # Ref: https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line

    # When using for longitude and latitude, this is only going to be useful
    # for small distances.

    denominator = math.sqrt( ( line_x2 - line_x1 )**2 + ( line_y2 - line_y1 )**2 )
    if abs( denominator ) < 0.0000001:
        return 0.0
    
    return ( abs( (( line_y1 - line_y2 ) * point_x)
                  + (( line_x2 - line_x1 ) * point_y)
                  + ( line_x1 * line_y2 )
                  - ( line_x2 * line_y1 ) ) / denominator )


def get_point_between_points( initial_longitude            : float,
                              initial_latitude             : float,
                              next_longitude               : float,
                              next_latitude                : float,
                              distance_from_initial_miles  : float ):

    # Ref: https://www.movable-type.co.uk/scripts/latlong.html

    earth_radius_miles = EARTH_RADIUS_AT_LAT_40_MILES

    ##########
    # Need radians, not degrees
    #
    initial_longitude = math.radians( initial_longitude )
    initial_latitude = math.radians( initial_latitude )
    next_longitude = math.radians( next_longitude )
    next_latitude = math.radians( next_latitude )

    ##########
    # First we compute the bearing between the two points

    delta_longitude = next_longitude - initial_longitude

    y = math.sin( delta_longitude ) * math.cos( next_latitude )
    x = (( math.cos( initial_latitude )
           * math.sin( next_latitude ) )
         - ( math.sin( initial_latitude )
             * math.cos( next_latitude )
             * math.cos( delta_longitude ) ))
    bearing_radians = math.atan2( y, x )

    ##########
    # Then we can extrapolate a distance from the initial point along that bearing.

    angular_distance = distance_from_initial_miles / earth_radius_miles

    latitude_radians = math.asin( ( math.sin( initial_latitude )
                                    * math.cos( angular_distance ) )
                                  + ( math.cos( initial_latitude )
                                      * math.sin( angular_distance )
                                      * math.cos( bearing_radians ) ))
    longitude_radians = initial_longitude + math.atan2( ( math.sin( bearing_radians )
                                                          * math.sin( angular_distance )
                                                          * math.cos( initial_latitude ) ),
                                                        math.cos( angular_distance )
                                                        - ( math.sin( initial_latitude )
                                                            * math.sin( latitude_radians )) )
    return ( math.degrees( longitude_radians ),
             math.degrees( latitude_radians ) )
    

def get_latitude_span( distance_miles : float ):
    """
    Return the latitude increment value necessary to span the given number
    of miles.
    """
    return distance_miles / MILES_PER_LATITUDE_LINE


def get_longitude_span( latitude : float, distance_miles : float ):
    """
    Return the longitude increment value necessary to span the given number
    of miles at the given latitude.
    """
    # 49 miles for each longitude line at 45 degrees north
    # 53 miles for each longitude line at 40 degrees north (middle of US)
    # 57 miles for each longitude line at 35 degrees north
    if math.isclose( distance_miles, 0.0, rel_tol = 1e-8 ):
        return 0.0
    miles_per_longitude_line = get_distance( latitude, 0.0, latitude, 1.0, miles=True )
    return float(distance_miles) / miles_per_longitude_line


def get_miles_per_latitude():
    """
    Return the number of miles in one line of the latitude meridian lines.
    This is invariant of longitude.
    """
    return MILES_PER_LATITUDE_LINE


def get_miles_per_longitude( reference_latitude : float = 40.0 ):
    """
    Return the number of miles in one line of the longitude meridian lines.
    This depends on the latitude, but if not provided, a nomial location is chosen.
    """
    return get_distance( lat1 = reference_latitude, lng1 = 0.0, lat2 = reference_latitude, lng2 = 1.0 )


def get_longitude_per_latitude( reference_latitude : float = 40.0 ):
    miles_per_latitude = get_miles_per_latitude()
    miles_per_longitude = get_miles_per_longitude( reference_latitude = reference_latitude )
    return miles_per_latitude / miles_per_longitude


def parse_long_lat_from_text( text : str, usa_biased = False ):
    """ Returns tuple of ( longitude, latitude ) """

    if not text:
        raise GeoPointParseError('Not text provided for longitude/latitude.')

    ##########
    # Special handling
    
    if 'google.com/maps' in text:
        m = re.search( r'\@([\d\.\-]+)\,([\d\.\-]+)\,', text )
        if m:
            return _validated_long_lat_values( latitude = float(m.group(1)),
                                               longitude = float(m.group(2)),
                                               usa_biased = usa_biased )
        m = re.search( r'll=([\d\.\-]+)\%2C([\d\.\-]+)\D', text )
        if m:
            return _validated_long_lat_values( latitude = float(m.group(1)),
                                               longitude = float(m.group(2)),
                                               usa_biased = usa_biased )
        raise GeoPointParseError('Could not find long/lat in google maps url.')

    text = text.replace("\n", " ").strip()

    ##########
    # Degrees only with direction letters (positive values only)
    
    m = re.search( r'([\d\.]*\d)[^\dNnSs]*([NnSs])\s+([\d\.]*\d)[^\dEeWw]*([EeWw])', text )
    if m:
        lat_degrees = float(m.group(1))
        long_degrees = float(m.group(3))
        if m.group(2).lower() == 's':
            lat_degrees *= -1.0
        if m.group(4).lower() == 'w':
            long_degrees *= -1.0
        return _validated_long_lat_values( lat_degrees, long_degrees, usa_biased = usa_biased )

    ##########
    # Degrees and minutes in decimal format
    
    m = re.search( r'(\d+)\D+([\d\.]*\d)[^\dNnSs]*([NnSs])\s+(\d+)\D+([\d\.]*\d)[^\dEeWw]*([EeWw])', text )
    if m:
        lat_degrees = float(m.group(1))
        lat_minutes = float(m.group(2))
        long_degrees = float(m.group(4))
        long_minutes = float(m.group(5))
        lat_degrees = lat_degrees + lat_minutes / 60.0
        long_degrees = long_degrees + long_minutes / 60.0
        if m.group(3).lower() == 's':
            lat_degrees *= -1.0
        if m.group(6).lower() == 'w':
            long_degrees *= -1.0
        return _validated_long_lat_values( lat_degrees, long_degrees, usa_biased = usa_biased )
    
    ##########
    # Degrees, minutes and seconds
    
    m = re.search( r'(\d+)\D+(\d+)\D+([\d\.]*\d)[^\dNnSs]*([NnSs])\s+(\d+)\D+(\d+)\D+([\d\.]*\d)[^\dEeWw]*([EeWw])', text )
    if m:
        lat_degrees = float(m.group(1))
        lat_minutes = float(m.group(2))
        lat_seconds = float(m.group(3))
        long_degrees = float(m.group(5))
        long_minutes = float(m.group(6))
        long_seconds = float(m.group(7))
        lat_degrees = lat_degrees + lat_minutes / 60.0 + lat_seconds / 3600.0
        long_degrees = long_degrees + long_minutes / 60.0 + long_seconds / 3600.0
        if m.group(4).lower() == 's':
            lat_degrees *= -1.0
        if m.group(8).lower() == 'w':
            long_degrees *= -1.0
        return _validated_long_lat_values( lat_degrees, long_degrees, usa_biased = usa_biased )
 
    ##########
    # Degress only in positive and negative (decimal degrees)
    #
    m = re.match( r'([\d\.\-]*\d)[^\d\-\.NnSs]+([\d\.\-]*\d)', text )
    if m:
        item1 = float(m.group(1))
        item2 = float(m.group(2))

        # The general convention is that latitude comes first, but we'll be
        # a little more flexible if we see a longitude value
        
        if item1 > 90.0:
            return ( item2, item1 )
        if item2 > 90.0:
            return ( item1, item2 )
        return _validated_long_lat_values( item1, item2, usa_biased = usa_biased )

    raise GeoPointParseError( 'Could not parse longitude and latitude.' )
            

def _validated_long_lat_values( latitude : float, longitude : float, usa_biased = False ):

    if usa_biased:
        # See if we should swap values to allow some robustness in parsing to the ordering
        if ( latitude < -50.0 ) and ( longitude > 0.0 ):
            longitude, latitude = latitude, longitude
        if ( longitude > -50.0 ):
            raise GeoPointParseError( f'Longitude {longitude} appears to be outside U.S. boundaries.' )
        if ( latitude < 0.0 ) or ( latitude > 75.0 ):
            raise GeoPointParseError( f'Latitude {latitude} appears to be outside U.S. boundaries.' )
    
    if abs(longitude) > 180.0:
        raise GeoPointParseError( f'Longitude is not in the valid range: -180 < longitude < 180.')
    if abs(latitude) > 90.0:
        raise GeoPointParseError( f'Latitude is not in the valid range: -90 < latitude < 90.')
    return ( latitude, longitude )


def normalize_state_name( name : str ):
    name = normalize_geo_name( name = name )
    return name


def normalize_county_name( name : str ):

    county_transform_map = {
        'De Kalb': 'DeKalb',
        'De Soto': 'DeSoto',
        'De Witt': 'DeWitt',
        'Dewitt': 'De Witt',
        'Dona Ana': 'Doña Ana',
        'La Porte': 'LaPorte',
        'La Salle': 'LaSalle',
        'Matanuska Susitna': 'Matanuska-Susitna',
        'Prince Georges': 'Prince George\'s',
        'Prince Wales Ketchikan': 'Prince of Wales-Hyder',
        'Queen Annes': 'Queen Anne\'s',
        'Valdez Cordova': 'Valdez-Cordova',
        'Wrangell Petersburg': 'Wrangell',
        'Yukon Koyukuk': 'Yukon-Koyukuk',
    }
    name = normalize_geo_name( name = name )
    if name in county_transform_map:
        name = county_transform_map[name]
    m = re.match( r'^(.+)\sCity$', name, re.IGNORECASE )
    if m:
        name = '%s (city)' % m.group(1)
    return name


def normalize_city_name( name : str ):
    name = normalize_geo_name( name = name )
    return name


def normalize_geo_name( name : str ):
    """" Common name normalizations used for Geographic places. """

    m = re.match( r'^(.*\s|)(st|st.|ste.)(\s.+)$', name, re.IGNORECASE )
    if m:
        name = '%sSaint%s' % ( m.group(1), m.group(3) )
        
    return name


def geo_name_similarity_ratio( name1 : str, name2 : str ):

    if name1.lower().endswith( ' city' ):
        name1 = name1[0:-5]
    if name2.lower().endswith( ' city' ):
        name2 = name2[0:-5]
    
    def is_junk( char ):
        return not char.isalnum()
    
    matcher = difflib.SequenceMatcher( isjunk = is_junk,
                                       a = name1.lower(),
                                       b = name2.lower() )
    return matcher.ratio()


def coordinates_to_label( longitude : float,
                          latitude : float ):
    return f'{latitude:.4f}, {longitude:.4f}'
