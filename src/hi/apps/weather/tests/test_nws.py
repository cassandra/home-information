from datetime import datetime
import logging
import unittest
from unittest.mock import Mock, patch

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.enums import (
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
    AlertCategory,
    AlertSeverity,
    AlertUrgency,
    AlertCertainty,
    AlertStatus,
    WeatherEventType,
)
from hi.apps.weather.transient_models import (
    BooleanDataPoint,
    NotablePhenomenon,
    NumericDataPoint,
    StringDataPoint,
    WeatherConditionsData,
    WeatherForecastData,
    IntervalWeatherForecast,
    Station,
    WeatherAlert,
)
from hi.apps.weather.weather_sources.nws import NationalWeatherService
from hi.transient_models import GeographicLocation
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase


logging.disable(logging.CRITICAL)


class TestNationalWeatherService( BaseTestCase ):

    def test_initialization(self):
        """Test NWS initialization."""
        nws = NationalWeatherService()
        self.assertEqual(nws.id, 'nws')
        self.assertEqual(nws.label, 'National Weather Service')
        self.assertEqual(nws.priority, 1)
        self.assertIsNotNone(nws.data_point_source)
        self.assertEqual(nws.data_point_source.id, 'nws')
        return

    def test_get_closest_station(self):

        test_stations_data = {
            "@context": [
                "https://geojson.org/geojson-ld/geojson-context.jsonld",
                {
                    "@version": "1.1",
                    "@vocab": "https://api.weather.gov/ontology#",
                    "bearing": {
                        "@type": "s:QuantitativeValue"
                    },
                    "city": "s:addressLocality",
                    "county": {
                        "@type": "@id"
                    },
                    "distance": {
                        "@id": "s:Distance",
                        "@type": "s:QuantitativeValue"
                    },
                    "forecastGridData": {
                        "@type": "@id"
                    },
                    "forecastOffice": {
                        "@type": "@id"
                    },
                    "geo": "http://www.opengis.net/ont/geosparql#",
                    "geometry": {
                        "@id": "s:GeoCoordinates",
                        "@type": "geo:wktLiteral"
                    },
                    "observationStations": {
                        "@container": "@list",
                        "@type": "@id"
                    },
                    "publicZone": {
                        "@type": "@id"
                    },
                    "s": "https://schema.org/",
                    "state": "s:addressRegion",
                    "unit": "http://codes.wmo.int/common/unit/",
                    "unitCode": {
                        "@id": "s:unitCode",
                        "@type": "@id"
                    },
                    "value": {
                        "@id": "s:value"
                    },
                    "wx": "https://api.weather.gov/ontology#"
                }
            ],
            "features": [
                {
                    "geometry": {
                        "coordinates": [
                            -97.76667,
                            30.31667
                        ],
                        "type": "Point"
                    },
                    "id": "https://api.weather.gov/stations/KATT",
                    "properties": {
                        "@id": "https://api.weather.gov/stations/KATT",
                        "@type": "wx:ObservationStation",
                        "county": "https://api.weather.gov/zones/county/TXC453",
                        "elevation": {
                            "unitCode": "wmoUnit:m",
                            "value": 199.9488
                        },
                        "fireWeatherZone": "https://api.weather.gov/zones/fire/TXZ192",
                        "forecast": "https://api.weather.gov/zones/forecast/TXZ192",
                        "name": "Austin City, Austin Camp Mabry",
                        "stationIdentifier": "KATT",
                        "timeZone": "America/Chicago"
                    },
                    "type": "Feature"
                },
                {
                    "geometry": {
                        "coordinates": [
                            -97.6798699,
                            30.18304
                        ],
                        "type": "Point"
                    },
                    "id": "https://api.weather.gov/stations/KAUS",
                    "properties": {
                        "@id": "https://api.weather.gov/stations/KAUS",
                        "@type": "wx:ObservationStation",
                        "county": "https://api.weather.gov/zones/county/TXC453",
                        "elevation": {
                            "unitCode": "wmoUnit:m",
                            "value": 148.1328
                        },
                        "fireWeatherZone": "https://api.weather.gov/zones/fire/TXZ192",
                        "forecast": "https://api.weather.gov/zones/forecast/TXZ192",
                        "name": "Austin-Bergstrom International Airport",
                        "stationIdentifier": "KAUS",
                        "timeZone": "America/Chicago"
                    },
                    "type": "Feature"
                },
                {
                    "geometry": {
                        "coordinates": [
                            -97.9659,
                            30.4967
                        ],
                        "type": "Point"
                    },
                    "id": "https://api.weather.gov/stations/KRYW",
                    "properties": {
                        "@id": "https://api.weather.gov/stations/KRYW",
                        "@type": "wx:ObservationStation",
                        "county": "https://api.weather.gov/zones/county/TXC453",
                        "elevation": {
                            "unitCode": "wmoUnit:m",
                            "value": 374.904
                        },
                        "fireWeatherZone": "https://api.weather.gov/zones/fire/TXZ192",
                        "forecast": "https://api.weather.gov/zones/forecast/TXZ192",
                        "name": "Lago Vista TX, Rusty Allen Airport",
                        "stationIdentifier": "KRYW",
                        "timeZone": "America/Chicago"
                    },
                    "type": "Feature"
                },
                {
                    "geometry": {
                        "coordinates": [
                            -102.21306,
                            30.04806
                        ],
                        "type": "Point"
                    },
                    "id": "https://api.weather.gov/stations/K6R6",
                    "properties": {
                        "@id": "https://api.weather.gov/stations/K6R6",
                        "@type": "wx:ObservationStation",
                        "county": "https://api.weather.gov/zones/county/TXC443",
                        "elevation": {
                            "unitCode": "wmoUnit:m",
                            "value": 707.136
                        },
                        "fireWeatherZone": "https://api.weather.gov/zones/fire/TXZ082",
                        "forecast": "https://api.weather.gov/zones/forecast/TXZ082",
                        "name": "Dryden - Terrell County Airport",
                        "stationIdentifier": "K6R6",
                        "timeZone": "America/Chicago"
                    },
                    "type": "Feature"
                }
            ],
            "observationStations": [
                "https://api.weather.gov/stations/KATT",
                "https://api.weather.gov/stations/KAUS",
                "https://api.weather.gov/stations/KRYW",
                "https://api.weather.gov/stations/K6R6"
            ],
            "pagination": {
                "next": "https://api.weather.gov/stations?id%5B0%5D=K11R&id%5B1%5D=K2R9&id%5B2%5D=K3T5&id%5B3%5D=K5C1&id%5B4%5D=K5T9&id%5B5%5D=K66R&id%5B6%5D=K6R6&id%5B7%5D=K8T6&id%5B8%5D=KACT&id%5B9%5D=KALI&id%5B10%5D=KAQO&id%5B11%5D=KARM&id%5B12%5D=KATT&id%5B13%5D=KAUS&id%5B14%5D=KBAZ&id%5B15%5D=KBBD&id%5B16%5D=KBEA&id%5B17%5D=KBMQ&id%5B18%5D=KCLL&id%5B19%5D=KCOT&id%5B20%5D=KCRP&id%5B21%5D=KCVB&id%5B22%5D=KCZT&id%5B23%5D=KDLF&id%5B24%5D=KDRT&id%5B25%5D=KDZB&id%5B26%5D=KECU&id%5B27%5D=KELA&id%5B28%5D=KERV&id%5B29%5D=KFTN&id%5B30%5D=KGOP&id%5B31%5D=KGRK&id%5B32%5D=KGTU&id%5B33%5D=KGYB&id%5B34%5D=KHDO&id%5B35%5D=KHYI&id%5B36%5D=KILE&id%5B37%5D=KJCT&id%5B38%5D=KLHB&id%5B39%5D=KLZZ&id%5B40%5D=KPEZ&id%5B41%5D=KPKV&id%5B42%5D=KPWG&id%5B43%5D=KRAS&id%5B44%5D=KRBO&id%5B45%5D=KRKP&id%5B46%5D=KRND&id%5B47%5D=KRWV&id%5B48%5D=KRYW&id%5B49%5D=KSAT&id%5B50%5D=KSEQ&id%5B51%5D=KSJT&id%5B52%5D=KSKF&id%5B53%5D=KSOA&id%5B54%5D=KSSF&id%5B55%5D=KT20&id%5B56%5D=KT35&id%5B57%5D=KT70&id%5B58%5D=KT74&id%5B59%5D=KT82&id%5B60%5D=KTPL&id%5B61%5D=KUVA&id%5B62%5D=KVCT&cursor=eyJzIjo1MDB9"
            },
            "type": "FeatureCollection"
        }

        test_data_list = [
            {
                'geographic_location': GeographicLocation(
                    latitude = 30.3,
                    longitude = -97.8,
                ),
                'expected': {
                    'station_id': 'KATT',
                    'name': 'Austin City, Austin Camp Mabry',
                    'geo_location': GeographicLocation(
                        latitude = 30.31667,
                        longitude = -97.76667,
                    ),
                    'station_url': 'https://api.weather.gov/stations/KATT',
                    'observations_url': 'https://api.weather.gov/stations/KATT/observations/latest',
                    'forecast_url': 'https://api.weather.gov/zones/forecast/TXZ192',
                },
            },
            {
                'geographic_location': GeographicLocation(
                    latitude = 30.2,
                    longitude = -97.8,
                ),
                'expected': {
                    'station_id': 'KAUS',
                    'name': 'Austin-Bergstrom International Airport',
                    'geo_location': GeographicLocation(
                        latitude = 30.18304,
                        longitude = -97.6798699,
                    ),
                    'station_url': 'https://api.weather.gov/stations/KAUS',
                    'observations_url': 'https://api.weather.gov/stations/KAUS/observations/latest',
                    'forecast_url': 'https://api.weather.gov/zones/forecast/TXZ192',
                },
            },
        ]

        nws = NationalWeatherService()
        
        for test_data in test_data_list:

            station = nws._get_closest_station(
                geographic_location = test_data['geographic_location'],
                stations_data = test_stations_data,
            )
            self.assertEqual( test_data['expected']['station_id'],
                              station.station_id,
                              test_data )
            self.assertEqual( test_data['expected']['name'],
                              station.name,
                              test_data )
            self.assertEqual( test_data['expected']['geo_location'].latitude,
                              station.geo_location.latitude,
                              test_data )
            self.assertEqual( test_data['expected']['geo_location'].longitude,
                              station.geo_location.longitude,
                              test_data )
            self.assertEqual( test_data['expected']['station_url'],
                              station.station_url,
                              test_data )
            self.assertEqual( test_data['expected']['observations_url'],
                              station.observations_url,
                              test_data )
            self.assertEqual( test_data['expected']['forecast_url'],
                              station.forecast_url,
                              test_data )
            continue
        return

    def test_parse_geometry_edge_cases(self):
        """Test geometry parsing with edge cases."""
        nws = NationalWeatherService()
        
        # Test None input
        result = nws._parse_geometry(None)
        self.assertIsNone(result)
        
        # Test empty dict
        result = nws._parse_geometry({})
        self.assertIsNone(result)
        
        # Test missing coordinates
        result = nws._parse_geometry({"type": "Point"})
        self.assertIsNone(result)
        
        # Test invalid coordinates (wrong length)
        result = nws._parse_geometry({"coordinates": [-97.7]})
        self.assertIsNone(result)
        
        # Test valid coordinates
        result = nws._parse_geometry({"coordinates": [-97.7, 30.3]})
        self.assertIsNotNone(result)
        self.assertEqual(result.longitude, -97.7)
        self.assertEqual(result.latitude, 30.3)
        return

    def test_parse_elevation_fallback(self):
        """Test elevation parsing with fallback behavior."""
        nws = NationalWeatherService()
        
        # Test with default value
        from hi.units import UnitQuantity
        default_elevation = UnitQuantity(100, 'm')
        result = nws._parse_elevation(None, default = default_elevation)
        self.assertEqual(result, default_elevation)
        
        # Test with invalid elevation data and no default (should return None)
        result = nws._parse_elevation({"invalid": "data"})
        self.assertIsNone(result)
        return

    def test_parse_nws_quantity__exceptions(self):
        test_data_list = [
            {
                "qualityControl": "Z",
                "unitCode": "_undefined_unit_",
                "value": 5
            },
            {
                "qualityControl": "Z",
                "unitCode": "_undefined_unit_",
                "maxValue": 5
            },
            {
                "qualityControl": "Z",
                "unitCode": "_undefined_unit_",
                "minValue": 5
            },
        ]
        nws = NationalWeatherService()
        for nws_data_dict in test_data_list:
            with self.assertRaises( ValueError ):
                nws._parse_nws_quantity( nws_data_dict = nws_data_dict )
            continue
        return
        
    def test_parse_nws_quantity__none(self):
        test_data_list = [
            None,
            {},
            { 'foo': 'bar' },
            {
                "qualityControl": "Z",
                "value": None,
            },
            {
                "qualityControl": "Z",
                "unitCode": "wmoUnit:mm",
            },
            {
                "qualityControl": "Z",
                "unitCode": "wmoUnit:mm",
                "value": None,
            },
            {
                "qualityControl": "Z",
                "unitCode": "wmoUnit:mm",
                "minValue": None,
            },
            {
                "qualityControl": "Z",
                "unitCode": "wmoUnit:mm",
                "maxValue": None
            },
            {
                "qualityControl": "Z",
                "unitCode": "wmoUnit:mm",
                "mainValue": None,
                "value": None,
                "maxValue": None,
            },
        ]
        nws = NationalWeatherService()
        for nws_data_dict in test_data_list:
            self.assertIsNone( nws._parse_nws_quantity( nws_data_dict = nws_data_dict ))
            continue
        return
        
    def test_parse_nws_quantity(self):
        test_data_list = [
            {
                "nws_data_dict": {
                    "qualityControl": "Z",
                    "unitCode": "wmoUnit:mm",
                    "value": 0
                },
                'for_min_value': False,
                'for_max_value': False,
                'expected': UnitQuantity( 0, 'millimeter' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:percent",
                    "value": 65.595209439964,
                },
                'for_min_value': False,
                'for_max_value': False,
                'expected': UnitQuantity( 65.595209439964, 'percent' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "value": 9.36,
                },
                'for_min_value': False,
                'for_max_value': False,
                'expected': UnitQuantity( 9.36, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 9.36,
                },
                'for_min_value': False,
                'for_max_value': False,
                'expected': UnitQuantity( 9.36, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "maxValue": 9.36,
                },
                'for_min_value': False,
                'for_max_value': False,
                'expected': UnitQuantity( 9.36, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 5.0,
                    "maxValue": 9.0,
                },
                'for_min_value': False,
                'for_max_value': False,
                'expected': UnitQuantity( 7.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 5.0,
                    "value": 11.0,
                    "maxValue": 9.0,
                },
                'for_min_value': False,
                'for_max_value': False,
                'expected': UnitQuantity( 11.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 11.0,
                },
                'for_min_value': True,
                'for_max_value': False,
                'expected': UnitQuantity( 11.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "value": 11.0,
                },
                'for_min_value': True,
                'for_max_value': False,
                'expected': UnitQuantity( 11.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "maxValue": 11.0,
                },
                'for_min_value': True,
                'for_max_value': False,
                'expected': UnitQuantity( 11.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 11.0,
                    "value": 8.0,
                },
                'for_min_value': True,
                'for_max_value': False,
                'expected': UnitQuantity( 11.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 11.0,
                    "maxValue": 8.0,
                },
                'for_min_value': True,
                'for_max_value': False,
                'expected': UnitQuantity( 11.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "value": 11.0,
                    "maxValue": 8.0,
                },
                'for_min_value': True,
                'for_max_value': False,
                'expected': UnitQuantity( 11.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 4.0,
                    "value": 11.0,
                    "maxValue": 8.0,
                },
                'for_min_value': True,
                'for_max_value': False,
                'expected': UnitQuantity( 4.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 4.0,
                },
                'for_min_value': False,
                'for_max_value': True,
                'expected': UnitQuantity( 4.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "value": 4.0,
                },
                'for_min_value': False,
                'for_max_value': True,
                'expected': UnitQuantity( 4.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "maxValue": 4.0,
                },
                'for_min_value': False,
                'for_max_value': True,
                'expected': UnitQuantity( 4.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 4.0,
                    "value": 9.0,
                },
                'for_min_value': False,
                'for_max_value': True,
                'expected': UnitQuantity( 9.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 4.0,
                    "maxValue": 9.0,
                },
                'for_min_value': False,
                'for_max_value': True,
                'expected': UnitQuantity( 9.0, 'kilometers /hour' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "minValue": 4.0,
                    "value": 12.0,
                    "maxValue": 9.0,
                },
                'for_min_value': False,
                'for_max_value': True,
                'expected': UnitQuantity( 9.0, 'kilometers /hour' ),
            },
        ]

        nws = NationalWeatherService()

        for test_data in test_data_list:
            result_quantity = nws._parse_nws_quantity(
                nws_data_dict = test_data['nws_data_dict'],
                for_min_value = test_data['for_min_value'],
                for_max_value = test_data['for_max_value'],
            )
            self.assertAlmostEqual( test_data['expected'].magnitude,
                                    result_quantity.magnitude,
                                    3, test_data )
            self.assertEqual( test_data['expected'].units,
                              result_quantity.units,
                              test_data )
            continue
        return

    def test_create_numeric_data_point__exceptions(self):
        test_data_list = [
            None,
            {},
            { 'foo': 'bar' },
            {
                "qualityControl": "Z",
                "value": None
            },
            {
                "qualityControl": "Z",
                "unitCode": "wmoUnit:mm",
            },
            {
                "qualityControl": "Z",
                "unitCode": "wmoUnit:mm",
                "value": None
            },
            {
                "qualityControl": "Z",
                "unitCode": "_undefined_unit_",
                "value": 5
            },
        ]
        now = datetimeproxy.now()

        nws = NationalWeatherService()
        station = Station(
            source = nws.data_point_source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
        
        for nws_data_dict in test_data_list:
            result_data_point = nws._create_numeric_data_point(
                nws_data_dict = nws_data_dict,
                source_datetime = now,
                station = station,
            )
            self.assertIsNone( result_data_point )
            continue
        return

    def test_create_numeric_data_point(self):
        test_data_list = [
            {
                "nws_data_dict": {
                    "qualityControl": "Z",
                    "unitCode": "wmoUnit:mm",
                    "value": 0
                },
                'expected': UnitQuantity( 0, 'millimeter' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:percent",
                    "value": 65.595209439964
                },
                'expected': UnitQuantity( 65.595209439964, 'percent' ),
            },
            {
                "nws_data_dict": {
                    "qualityControl": "V",
                    "unitCode": "wmoUnit:km_h-1",
                    "value": 9.36
                },
                'expected': UnitQuantity( 9.36, 'kilometers /hour' ),
            },
        ]

        now = datetimeproxy.now()

        nws = NationalWeatherService()
        station = Station(
            source = nws.data_point_source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )

        for test_data in test_data_list:
            result_data_point = nws._create_numeric_data_point(
                nws_data_dict = test_data['nws_data_dict'],
                source_datetime = now,
                station = station,
            )
            self.assertEqual( nws.data_point_source.id,
                              result_data_point.station.source.id,
                              test_data )
            self.assertEqual( now, result_data_point.source_datetime )
            result_quantity = result_data_point.quantity
            self.assertAlmostEqual( test_data['expected'].magnitude, result_quantity.magnitude, 3, test_data )
            self.assertEqual( test_data['expected'].units, result_quantity.units, test_data )
            continue
        return

    def test_parse_cloud_layers(self):
        source_datetime = datetimeproxy.now()
        nws = NationalWeatherService()
        station = Station(
            source = nws.data_point_source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )

        test_data_list = [
            {
                'label': 'No Reported Cloud Layers (Empty List)',
                'properties': {
                    "cloudLayers": []
                },
                'expected_cloud_ceiling': None,
                'expected_cloud_cover': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 0, 'percent' ),
                ),
            },
            {
                'label': 'Clear Skies (SKC)',
                'properties': {
                    "cloudLayers": [
                        {
                            "amount": "SKC",
                            "base": None
                        }
                    ]
                },
                'expected_cloud_ceiling': None,
                'expected_cloud_cover': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 0, 'percent' ),
                ),
            },
            {
                'label': 'Few Clouds at 3,000 ft (FEW)',
                'properties': {
                    "cloudLayers": [
                        {
                            "amount": "FEW",
                            "base": {
                                "value": 3000,
                                "unitCode": "unit:ft"
                            }
                        }
                    ]
                },
                'expected_cloud_ceiling': None,
                'expected_cloud_cover': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 25, 'percent' ),
                ),
            },
            {
                'label': 'Scattered Clouds at Multiple Levels (SCT)',
                'properties': {
                    "cloudLayers": [
                        {
                            "amount": "SCT",
                            "base": {
                                "value": 2000,
                                "unitCode": "unit:ft"
                            }
                        },
                        {
                            "amount": "SCT",
                            "base": {
                                "value": 5000,
                                "unitCode": "unit:ft"
                            }
                        }
                    ]
                },
                'expected_cloud_ceiling': None,
                'expected_cloud_cover': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 50, 'percent' ),
                ),
            },
            {
                'label': 'Broken Clouds (BKN) with Ceiling at 8,000 ft',
                'properties': {
                    "cloudLayers": [
                        {
                            "amount": "BKN",
                            "base": {
                                "value": 8000,
                                "unitCode": "unit:ft"
                            }
                        }
                    ]
                },
                'expected_cloud_ceiling': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 8000, 'feet' ),
                )    ,
                'expected_cloud_cover': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 87.5, 'percent' ),
                ),
            },
            {
                'label': 'Overcast Sky (OVC) at 12,000 ft',
                'properties': {
                    "cloudLayers": [
                        {
                            "amount": "OVC",
                            "base": {
                                "value": 12000,
                                "unitCode": "unit:ft"
                            }
                        }
                    ]
                },
                'expected_cloud_ceiling': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 12000, 'feet' ),
                )    ,
                'expected_cloud_cover': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 100, 'percent' ),
                ),
            },
            {
                'label': 'Vertical Visibility (VV) at 300 ft (Obscured Sky)',
                'properties': {
                    "cloudLayers": [
                        {
                            "amount": "VV",
                            "base": {
                                "value": 300,
                                "unitCode": "unit:ft"
                            }
                        }
                    ]
                },
                'expected_cloud_ceiling': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 300, 'feet' ),
                )    ,
                'expected_cloud_cover': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 100, 'percent' ),
                ),
            },
            {
                'label': 'Multiple Cloud Layers (Scattered + Overcast)',
                'properties': {
                    "cloudLayers": [
                        {
                            "amount": "SCT",
                            "base": {
                                "value": 5000,
                                "unitCode": "unit:ft"
                            }
                        },
                        {
                            "amount": "OVC",
                            "base": {
                                "value": 10000,
                                "unitCode": "unit:ft"
                            }
                        }
                    ]
                },
                'expected_cloud_ceiling': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 10000, 'feet' ),
                )    ,
                'expected_cloud_cover': NumericDataPoint(
                    station = station,
                    source_datetime = source_datetime,
                    quantity_ave = UnitQuantity( 100, 'percent' ),
                ),
            },
        ]

        for test_data in test_data_list:
            weather_conditions_data = WeatherConditionsData()
            
            nws._parse_cloud_layers(
                properties_data = test_data['properties'],
                weather_conditions_data = weather_conditions_data,
                source_datetime =source_datetime,
                station = station,
            )

            result_cloud_ceiling = weather_conditions_data.cloud_ceiling
            expected_cloud_ceiling = test_data['expected_cloud_ceiling']
            if expected_cloud_ceiling is None:
                self.assertIsNone( result_cloud_ceiling )
            else:
                self.assertAlmostEqual( expected_cloud_ceiling.quantity.magnitude,
                                        result_cloud_ceiling.quantity.magnitude,
                                        3, test_data['label'] )
                self.assertEqual( expected_cloud_ceiling.quantity.units,
                                  result_cloud_ceiling.quantity.units,
                                  test_data['label'] )                

            result_cloud_cover = weather_conditions_data.cloud_cover
            expected_cloud_cover = test_data['expected_cloud_cover']
            if expected_cloud_cover is None:
                self.assertIsNone( result_cloud_cover )
            else:
                self.assertAlmostEqual( expected_cloud_cover.quantity.magnitude,
                                        result_cloud_cover.quantity.magnitude,
                                        3, test_data['label'] )
                self.assertEqual( expected_cloud_cover.quantity.units,
                                  result_cloud_cover.quantity.units,
                                  test_data['label'] )                
            continue
        return

    def test_parse_present_weather(self):
        source_datetime = datetimeproxy.now()
        nws = NationalWeatherService()
        station = Station(
            source = nws.data_point_source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )

        test_data_list = [
            {
                'label': 'No Significant Weather (Empty List)',
                'properties': {
                    "presentWeather": []
                },
                'expected_list': [],
            },
            {
                'label': 'Light Rain',
                'properties': {
                    "presentWeather": [
                        {
                            "intensity": "light",
                            "modifier": "none",
                            "weather": "rain",
                            "inVicinity": False,
                            "rawString": "-RA"
                        }
                    ]
                },
                'expected_list': [
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.RAIN,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.NONE,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.LIGHT,
                        in_vicinity = False,
                    ),
                ]
            },
            {
                'label': 'Heavy Snow Showers',
                'properties': {
                    "presentWeather": [
                        {
                            "intensity": "heavy",
                            "modifier": "showers",
                            "weather": "snow",
                            "inVicinity": False,
                            "rawString": "+SHSN"
                        }
                    ]
                },
                'expected_list': [
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.SNOW,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.SHOWERS,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.HEAVY,
                        in_vicinity = False,
                    ),
                ]
            },
            {
                'label': 'Thunderstorms Near the Station',
                'properties': {
                    "presentWeather": [
                        {
                            "intensity": "moderate",
                            "modifier": "thunderstorm",
                            "weather": "rain",
                            "inVicinity": True,
                            "rawString": "VCTSRA"
                        }
                    ]
                },
                'expected_list': [
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.RAIN,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.THUNDERSTORMS,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.MODERATE,
                        in_vicinity = True,
                    ),
                ]
            },
            {
                'label': 'Freezing Fog',
                'properties': {
                    "presentWeather": [
                        {
                            "intensity": "none",
                            "modifier": "freezing",
                            "weather": "fog",
                            "inVicinity": False,
                            "rawString": "FZFG"
                        }
                    ]
                },
                'expected_list': [
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.FOG,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.FREEZING,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.MODERATE,
                        in_vicinity = False,
                    ),
                ]
            },
            {
                'label': 'Multiple Weather Conditions (Rain and Mist)',
                'properties': {
                    "presentWeather": [
                        {
                            "intensity": "moderate",
                            "modifier": "none",
                            "weather": "rain",
                            "inVicinity": False,
                            "rawString": "RA"
                        },
                        {
                            "intensity": "light",
                            "modifier": "none",
                            "weather": "mist",
                            "inVicinity": False,
                            "rawString": "BR"
                        }
                    ]
                },
                'expected_list': [
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.RAIN,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.NONE,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.MODERATE,
                        in_vicinity = False,
                    ),
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.MIST,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.NONE,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.LIGHT,
                        in_vicinity = False,
                    ),
                ]
            },
            {
                'label': 'Dust Storm (Severe)',
                'properties': {
                    "presentWeather": [
                        {
                            "intensity": "heavy",
                            "modifier": "none",
                            "weather": "dust",
                            "inVicinity": False,
                            "rawString": "+DS"
                        }
                    ]
                },
                'expected_list': [
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.DUSTSTORM,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.NONE,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.HEAVY,
                        in_vicinity = False,
                    ),
                ]
            },
            {
                'label': 'Haze Without a Modifier',
                'properties': {
                    "presentWeather": [
                        {
                            "intensity": "none",
                            "modifier": "none",
                            "weather": "haze",
                            "inVicinity": False,
                            "rawString": "HZ"
                        }
                    ]
                },
                'expected_list': [
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.HAZE,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.NONE,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.MODERATE,
                        in_vicinity = False,
                    ),
                ]
            },
            {
                'label': 'Blowing Snow',
                'properties': {
                    "presentWeather": [
                        {
                            "intensity": "moderate",
                            "modifier": "blowing",
                            "weather": "snow",
                            "inVicinity": False,
                            "rawString": "BLSN"
                        }
                    ]
                },
                'expected_list': [
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.SNOW,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.BLOWING,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.MODERATE,
                        in_vicinity = False,
                    ),
                ]
            },
            {
                'label': 'Ice Pellets and Freezing Rain Mixed',
                'properties': {
                    "presentWeather": [
                        {
                            "intensity": "moderate",
                            "modifier": "none",
                            "weather": "ice pellets",
                            "inVicinity": False,
                            "rawString": "PL"
                        },
                        {
                            "intensity": "light",
                            "modifier": "freezing",
                            "weather": "rain",
                            "inVicinity": False,
                            "rawString": "-FZRA"
                        },
                    ],
                },
                'expected_list': [
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.ICE_PELLETS,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.NONE,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.MODERATE,
                        in_vicinity = False,
                    ),
                    NotablePhenomenon(
                        weather_phenomenon = WeatherPhenomenon.RAIN,
                        weather_phenomenon_modifier = WeatherPhenomenonModifier.FREEZING,
                        weather_phenomenon_intensity = WeatherPhenomenonIntensity.LIGHT,
                        in_vicinity = False,
                    ),
                ],
            },
        ]            
        
        for test_data in test_data_list:
            weather_conditions_data = WeatherConditionsData()
            
            nws._parse_present_weather(
                properties_data = test_data['properties'],
                weather_conditions_data = weather_conditions_data,
                source_datetime =source_datetime,
                station = station,
            )

            expected_list = test_data['expected_list']
            if expected_list:
                result_list = weather_conditions_data.notable_phenomenon_data.list_value
                self.assertEqual( len(expected_list), len(result_list), test_data['label'] )
                for expected_phenomenon, result_phenomenon in zip( expected_list, result_list ):
                    self.assertEqual( expected_phenomenon.weather_phenomenon,
                                      result_phenomenon.weather_phenomenon,
                                      test_data['label'] )
                    self.assertEqual( expected_phenomenon.weather_phenomenon_modifier,
                                      result_phenomenon.weather_phenomenon_modifier,
                                      test_data['label'] )
                    self.assertEqual( expected_phenomenon.weather_phenomenon_intensity,
                                      result_phenomenon.weather_phenomenon_intensity,
                                      test_data['label'] )
                    self.assertEqual( expected_phenomenon.in_vicinity,
                                      result_phenomenon.in_vicinity,
                                      test_data['label'] )
                    continue
            else:
                self.assertIsNone( weather_conditions_data.notable_phenomenon_data, test_data['label'] )
            continue
        return

    @patch('hi.apps.weather.weather_sources.nws.requests.get')
    def test_get_points_data_from_api(self, mock_get):
        """Test API call for points data."""
        nws = NationalWeatherService()
        test_location = GeographicLocation(latitude = 30.27, longitude = -97.74)
        
        # Mock successful response
        mock_response_data = {
            "properties": {
                "gridId": "EWX",
                "observationStations": "https://api.weather.gov/gridpoints/EWX/158,90/stations"
            }
        }
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = nws._get_points_data_from_api(test_location)
        
        self.assertEqual(result, mock_response_data)
        mock_get.assert_called_once()
        # Verify correct URL was called
        expected_url = f'https://api.weather.gov/points/{test_location.latitude},{test_location.longitude}'
        actual_url = mock_get.call_args[0][0]
        self.assertEqual(actual_url, expected_url)
        return

    @patch('hi.apps.weather.weather_sources.nws.requests.get')
    def test_get_points_data_from_api_error(self, mock_get):
        """Test API call error handling."""
        nws = NationalWeatherService()
        test_location = GeographicLocation(latitude = 30.27, longitude = -97.74)
        
        # Mock HTTP error
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response
        
        with self.assertRaises(Exception):
            nws._get_points_data_from_api(test_location)
        return
    
    def test_parse_observations_data(self):
        nws = NationalWeatherService()
        timestamp_str = '2025-02-20T04:51:00+00:00'
        source_datetime = datetime.fromisoformat( timestamp_str )
        description_short = 'Cloudy'
        station = Station(
            source = nws.data_point_source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )
            
        test_data_list = [
            {
                'label': 'Response from Feb 20, 2025 for Austin, TX',
                'response': {
                    "@context": [
                        "https://geojson.org/geojson-ld/geojson-context.jsonld",
                        {
                            "@version": "1.1",
                            "@vocab": "https://api.weather.gov/ontology#",
                            "bearing": {
                                "@type": "s:QuantitativeValue"
                            },
                            "city": "s:addressLocality",
                            "county": {
                                "@type": "@id"
                            },
                            "distance": {
                                "@id": "s:Distance",
                                "@type": "s:QuantitativeValue"
                            },
                            "forecastGridData": {
                                "@type": "@id"
                            },
                            "forecastOffice": {
                                "@type": "@id"
                            },
                            "geo": "http://www.opengis.net/ont/geosparql#",
                            "geometry": {
                                "@id": "s:GeoCoordinates",
                                "@type": "geo:wktLiteral"
                            },
                            "publicZone": {
                                "@type": "@id"
                            },
                            "s": "https://schema.org/",
                            "state": "s:addressRegion",
                            "unit": "http://codes.wmo.int/common/unit/",
                            "unitCode": {
                                "@id": "s:unitCode",
                                "@type": "@id"
                            },
                            "value": {
                                "@id": "s:value"
                            },
                            "wx": "https://api.weather.gov/ontology#"
                        }
                    ],
                    "geometry": {
                        "coordinates": [
                            -97.77,
                            30.32
                        ],
                        "type": "Point"
                    },
                    "id": "https://api.weather.gov/stations/KATT/observations/2025-02-20T04:51:00+00:00",
                    "properties": {
                        "@id": "https://api.weather.gov/stations/KATT/observations/2025-02-20T04:51:00+00:00",
                        "@type": "wx:ObservationStation",
                        "barometricPressure": {
                            "qualityControl": "V",
                            "unitCode": "wmoUnit:Pa",
                            "value": 103420
                        },
                        "cloudLayers": [
                            {
                                "amount": "OVC",
                                "base": {
                                    "unitCode": "wmoUnit:m",
                                    "value": 880
                                }
                            }
                        ],
                        "dewpoint": {
                            "qualityControl": "V",
                            "unitCode": "wmoUnit:degC",
                            "value": -9.4
                        },
                        "elevation": {
                            "unitCode": "wmoUnit:m",
                            "value": 198
                        },
                        "heatIndex": {
                            "qualityControl": "V",
                            "unitCode": "wmoUnit:degC",
                            "value": None
                        },
                        "icon": "https://api.weather.gov/icons/land/night/ovc?size=medium",
                        "maxTemperatureLast24Hours": {
                            "unitCode": "wmoUnit:degC",
                            "value": None
                        },
                        "minTemperatureLast24Hours": {
                            "unitCode": "wmoUnit:degC",
                            "value": None
                        },
                        "precipitationLast3Hours": {
                            "qualityControl": "Z",
                            "unitCode": "wmoUnit:mm",
                            "value": None
                        },
                        "precipitationLast6Hours": {
                            "qualityControl": "Z",
                            "unitCode": "wmoUnit:mm",
                            "value": None
                        },
                        "precipitationLastHour": {
                            "qualityControl": "Z",
                            "unitCode": "wmoUnit:mm",
                            "value": None
                        },
                        "presentWeather": [],
                        "rawMessage": "KATT 200451Z AUTO 35005KT 10SM OVC029 M04/M09 A3054 RMK AO2",
                        "relativeHumidity": {
                            "qualityControl": "V",
                            "unitCode": "wmoUnit:percent",
                            "value": 65.595209439964
                        },
                        "seaLevelPressure": {
                            "qualityControl": "V",
                            "unitCode": "wmoUnit:Pa",
                            "value": 103580
                        },
                        "station": "https://api.weather.gov/stations/KATT",
                        "temperature": {
                            "qualityControl": "V",
                            "unitCode": "wmoUnit:degC",
                            "value": -3.9
                        },
                        "textDescription": description_short,
                        "timestamp": timestamp_str,
                        "visibility": {
                            "qualityControl": "C",
                            "unitCode": "wmoUnit:m",
                            "value": 16090
                        },
                        "windChill": {
                            "qualityControl": "V",
                            "unitCode": "wmoUnit:degC",
                            "value": -7.757550390365555
                        },
                        "windDirection": {
                            "qualityControl": "V",
                            "unitCode": "wmoUnit:degree_(angle)",
                            "value": 350
                        },
                        "windGust": {
                            "qualityControl": "Z",
                            "unitCode": "wmoUnit:km_h-1",
                            "value": None
                        },
                        "windSpeed": {
                            "qualityControl": "V",
                            "unitCode": "wmoUnit:km_h-1",
                            "value": 9.36
                        }
                    },
                    "type": "Feature"
                },
                'expected': WeatherConditionsData(
                    barometric_pressure = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( 103420, 'Pa' ),
                    ),
                    dew_point = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( -9.4, 'degC' ),
                    ),
                    heat_index = None,
                    temperature_max_last_24h = None,
                    temperature_min_last_24h = None,
                    precipitation_last_3h = None,
                    precipitation_last_6h = None,
                    precipitation_last_hour = None,
                    relative_humidity = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( 65.595209439964, 'percent' ),
                    ),
                    sea_level_pressure = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( 103580, 'Pa' ),
                    ),
                    temperature = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( -3.9, 'degC' ),
                    ),
                    visibility = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( 16090, 'meters' ),
                    ),
                    wind_chill = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( -7.757550390365555, 'degC' ),
                    ),
                    wind_direction = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( 350, 'degrees' ),
                    ),
                    windspeed = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( 9.36, 'km / h' ),
                    ),
                    description_short = StringDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        value = description_short,
                    ),
                    cloud_ceiling = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( 880, 'meters' ),
                    ),
                    cloud_cover = NumericDataPoint(
                        station = station,
                        source_datetime = source_datetime,
                        quantity_ave = UnitQuantity( 100, 'percent' ),
                    ),
                    notable_phenomenon_data = None,
                )
            }
        ]        

        for test_data in test_data_list:
            expected = test_data['expected']
            result = nws._parse_observation_data(
                test_data['response'],
                station = station,
            )

            self._compare_numeric_data_point( expected.barometric_pressure,
                                              result.barometric_pressure,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.dew_point,
                                              result.dew_point,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.heat_index,
                                              result.heat_index,
                                              test_data['label'] )
            self._compare_numeric_data_point( expected.temperature_max_last_24h,
                                              result.temperature_max_last_24h,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.temperature_min_last_24h,
                                              result.temperature_min_last_24h,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.precipitation_last_3h,
                                              result.precipitation_last_3h,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.precipitation_last_6h,
                                              result.precipitation_last_6h,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.precipitation_last_hour,
                                              result.precipitation_last_hour,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.relative_humidity,
                                              result.relative_humidity,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.sea_level_pressure,
                                              result.sea_level_pressure,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.temperature,
                                              result.temperature,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.visibility,
                                              result.visibility,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.wind_chill,
                                              result.wind_chill,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.wind_direction,
                                              result.wind_direction,
                                              test_data['label']  )
            self._compare_statistic_data_point( expected.windspeed,
                                                result.windspeed,
                                                test_data['label']  )
            self._compare_numeric_data_point( expected.cloud_ceiling,
                                              result.cloud_ceiling,
                                              test_data['label']  )
            self._compare_numeric_data_point( expected.cloud_cover,
                                              result.cloud_cover,
                                              test_data['label']  )

            self.assertEqual( expected.description_short.value,
                              result.description_short.value,
                              test_data['label']  )

            if expected.notable_phenomenon_data:
                self.assertEqual( len(expected.notable_phenomenon_data.list_value),
                                  len(result.notable_phenomenon_data.list_value),
                                  test_data['label']  )
                for expected_phenomenon, result_phenomenon in zip( expected.notable_phenomenon_data.list_value,
                                                                   result.notable_phenomenon_data.list_value ):
                    self.assertEqual( expected_phenomenon.weather_phenomenon,
                                      result_phenomenon.weather_phenomenon,
                                      test_data['label'] )
                    self.assertEqual( expected_phenomenon.weather_phenomenon_modifier,
                                      result_phenomenon.weather_phenomenon_modifier,
                                      test_data['label'] )
                    self.assertEqual( expected_phenomenon.weather_phenomenon_intensity,
                                      result_phenomenon.weather_phenomenon_intensity,
                                      test_data['label'] )
                    self.assertEqual( expected_phenomenon.in_vicinity,
                                      result_phenomenon.in_vicinity,
                                      test_data['label'] )
                    continue
            else:
                self.assertIsNone( result.notable_phenomenon_data, test_data['label']  )
                
            continue
        return

    def test_parse_forecast_data(self):
        nws = NationalWeatherService()
        timestamp_str = '2025-02-28T20:36:26+00:00'
        source_datetime = datetime.fromisoformat( timestamp_str )
        station = Station(
            source = nws.data_point_source,
            station_id = 'test',
            name = 'Testing',
            geo_location = None,
            station_url = None,
            observations_url = None,
            forecast_url = None,
        )

        test_data_list = [
            {
                'label': 'Response from Feb 20, 2025 for Austin, TX',
                'response': {
                    "@context": [
                        "https://geojson.org/geojson-ld/geojson-context.jsonld",
                        {
                            "@version": "1.1",
                            "@vocab": "https://api.weather.gov/ontology#",
                            "geo": "http://www.opengis.net/ont/geosparql#",
                            "unit": "http://codes.wmo.int/common/unit/",
                            "wx": "https://api.weather.gov/ontology#"
                        }
                    ],
                    "geometry": {
                        "coordinates": [
                            [
                                [
                                    -97.7255,
                                    30.2592
                                ],
                                [
                                    -97.726,
                                    30.282
                                ],
                                [
                                    -97.7524,
                                    30.2815
                                ],
                                [
                                    -97.75179999999999,
                                    30.2588
                                ],
                                [
                                    -97.7255,
                                    30.2592
                                ]
                            ]
                        ],
                        "type": "Polygon"
                    },
                    "properties": {
                        "elevation": {
                            "unitCode": "wmoUnit:m",
                            "value": 155.1432
                        },
                        "forecastGenerator": "BaselineForecastGenerator",
                        "generatedAt": timestamp_str,
                        "periods": [
                            {
                                "detailedForecast": "Sunny, with a high near 76. South wind around 0 mph.",
                                "endTime": "2025-02-28T18:00:00-06:00",
                                "icon": "https://api.weather.gov/icons/land/day/few?size=medium",
                                "isDaytime": True,
                                "name": "This Afternoon",
                                "number": 1,
                                "probabilityOfPrecipitation": {
                                    "unitCode": "wmoUnit:percent",
                                    "value": None
                                },
                                "shortForecast": "Sunny",
                                "startTime": "2025-02-28T14:00:00-06:00",
                                "temperature": {
                                    "unitCode": "wmoUnit:degC",
                                    "value": 24.444444444444443
                                },
                                "temperatureTrend": "",
                                "windDirection": "",
                                "windGust": None,
                                "windSpeed": {
                                    "unitCode": "wmoUnit:km_h-1",
                                    "value": 0
                                }
                            },
                            {
                                "detailedForecast": "Mostly clear, with a low around 52. South southwest wind around 0 mph.",
                                "endTime": "2025-03-01T06:00:00-06:00",
                                "icon": "https://api.weather.gov/icons/land/night/few?size=medium",
                                "isDaytime": False,
                                "name": "Tonight",
                                "number": 2,
                                "probabilityOfPrecipitation": {
                                    "unitCode": "wmoUnit:percent",
                                    "value": None
                                },
                                "shortForecast": "Mostly Clear",
                                "startTime": "2025-02-28T18:00:00-06:00",
                                "temperature": {
                                    "unitCode": "wmoUnit:degC",
                                    "value": 11.11111111111111
                                },
                                "temperatureTrend": "",
                                "windDirection": "",
                                "windGust": None,
                                "windSpeed": {
                                    "unitCode": "wmoUnit:km_h-1",
                                    "value": 0
                                }
                            },
                        ],
                        "units": "us",
                        "updateTime": "2025-02-28T20:06:34+00:00",
                        "validTimes": "2025-02-28T14:00:00+00:00/P7DT14H"
                    },
                    "type": "Feature"
                },
                'expected': [
                    {
                        'start': datetime.fromisoformat( '2025-02-28T14:00:00-06:00' ),
                        'end': datetime.fromisoformat('2025-02-28T18:00:00-06:00' ),
                        'name': StringDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = 'This Afternoon',
                        ),
                        'description_short': StringDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = 'Sunny',
                        ),
                        'description_long': StringDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = 'Sunny, with a high near 76. South wind around 0 mph.',
                        ),
                        'is_daytime': BooleanDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = True,
                        ),
                        'precipitation_probability': None,
                        'dew_point': None,
                        'relative_humidity': None,
                        'temperature': NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_ave = UnitQuantity( 24.444444444444443, 'degC' ),
                        ),
                        'windspeed': NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_ave = UnitQuantity( 0, 'km / h' ),
                        ),
                        'wind_direction': None,
                    },
                    {
                        'start': datetime.fromisoformat( '2025-02-28T18:00:00-06:00' ),
                        'end': datetime.fromisoformat('2025-03-01T06:00:00-06:00' ),
                        'name': StringDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value ='Tonight',
                        ),
                        'description_short': StringDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value ='Mostly Clear',
                        ),
                        'description_long': StringDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value ='Mostly clear, with a low around 52. South southwest wind around 0 mph.',
                        ),
                        'is_daytime': BooleanDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            value = False,
                        ),
                        'precipitation_probability': None,
                        'dew_point': None,
                        'relative_humidity': None,
                        'temperature': NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_ave = UnitQuantity( 11.1111111111, 'degC' ),
                        ),
                        'windspeed': NumericDataPoint(
                            station = station,
                            source_datetime = source_datetime,
                            quantity_ave = UnitQuantity( 0, 'km / h' ),
                        ),
                        'wind_direction': None,
                    },
                ],
            },
        ]
        
        for test_data in test_data_list:
            expected = test_data['expected']
            result_list = nws._parse_forecast_data(
                test_data['response'],
                station = station,
            )
            self.assertEqual( len(result_list), len(test_data['expected']) )
            for idx, ( expected, result ) in enumerate( zip( test_data['expected'], result_list )):
                
                self.assertEqual( expected['start'],
                                  result.interval.start,
                                  f'[{idx}] %s' % test_data['label'] )
                self.assertEqual( expected['end'],
                                  result.interval.end,
                                  f'[{idx}] %s' % test_data['label'] )
                self.assertEqual( expected['name'].value,
                                  result.interval.name.value,
                                  f'[{idx}] %s' % test_data['label'] )
                self.assertEqual( expected['description_short'].value,
                                  result.data.description_short.value,
                                  f'[{idx}] %s' % test_data['label'] )
                self.assertEqual( expected['description_long'].value,
                                  result.data.description_long.value,
                                  f'[{idx}] %s' % test_data['label'] )
                self.assertEqual( expected['is_daytime'].value,
                                  result.data.is_daytime.value,
                                  f'[{idx}] %s' % test_data['label'] )
                self._compare_numeric_data_point( expected['precipitation_probability'],
                                                  result.data.precipitation_probability,
                                                  f'[{idx}] %s' % test_data['label']  )
                self._compare_numeric_data_point( expected['dew_point'],
                                                  result.data.dew_point,
                                                  f'[{idx}] %s' % test_data['label']  )
                self._compare_statistic_data_point( expected['temperature'],
                                                    result.data.temperature,
                                                    f'[{idx}] %s' % test_data['label']  )
                self._compare_statistic_data_point( expected['windspeed'],
                                                    result.data.windspeed,
                                                    f'[{idx}] %s' % test_data['label']  )
                self._compare_numeric_data_point( expected['wind_direction'],
                                                  result.data.wind_direction,
                                                  f'[{idx}] %s' % test_data['label']  )
                continue
            continue

        return
    
    def _compare_numeric_data_point( self, expected, result, label ):
        if expected is None:
            self.assertIsNone( result, label )
            return
            
        self.assertEqual( expected.source, result.source, label )
        self.assertEqual( expected.source_datetime, result.source_datetime, label )
        self.assertAlmostEqual( expected.quantity.magnitude, result.quantity.magnitude, 3, label )
        self.assertEqual( expected.quantity.units, result.quantity.units, label )
        return
    
    def _compare_statistic_data_point( self, expected, result, label ):
        if expected is None:
            self.assertIsNone( result, label )
            return
            
        self.assertEqual( expected.source, result.source, label )
        self.assertEqual( expected.source_datetime, result.source_datetime, label )
        if expected.quantity_min is None:
            self.assertIsNone( result.quantity_min, label )
        else:
            self.assertAlmostEqual( expected.quantity_min.magnitude, result.quantity_min.magnitude, 3, label )
            self.assertEqual( expected.quantity_min.units, result.quantity_min.units, label )

        if expected.quantity_ave is None:
            self.assertIsNone( result.quantity_ave, label )
        else:
            self.assertAlmostEqual( expected.quantity_ave.magnitude, result.quantity_ave.magnitude, 3, label )
            self.assertEqual( expected.quantity_ave.units, result.quantity_ave.units, label )

        if expected.quantity_max is None:
            self.assertIsNone( result.quantity_max, label )
        else:
            self.assertAlmostEqual( expected.quantity_max.magnitude, result.quantity_max.magnitude, 3, label )
            self.assertEqual( expected.quantity_max.units, result.quantity_max.units, label )

        return

    @patch('hi.apps.weather.weather_sources.nws.requests.get')
    def test_get_alerts_data_from_api_success(self, mock_get):
        """Test successful API call for weather alerts - HIGH VALUE for alerts integration."""
        # Mock successful API response based on NWS alerts API format
        mock_response_data = {
            "@context": [
                "https://geojson.org/geojson-ld/geojson-context.jsonld",
                {"@version": "1.1"}
            ],
            "type": "FeatureCollection",
            "title": "Current watches, warnings, and advisories for 30.27 N, 97.74 W",
            "updated": "2024-03-15T20:00:00Z",
            "features": [
                {
                    "id": "urn:oid:2.49.0.1.840.0.123abc",
                    "type": "Feature",
                    "geometry": None,
                    "properties": {
                        "@type": "wx:Alert",
                        "id": "urn:oid:2.49.0.1.840.0.123abc",
                        "areaDesc": "Travis; Williamson",
                        "geocode": {
                            "SAME": ["048453", "048491"],
                            "UGC": ["TXZ191", "TXZ192"]
                        },
                        "status": "Actual",
                        "messageType": "Alert",
                        "category": "Met",
                        "severity": "Moderate",
                        "certainty": "Likely",
                        "urgency": "Expected",
                        "event": "Flood Warning",
                        "effective": "2024-03-15T18:00:00-05:00",
                        "expires": "2024-03-16T06:00:00-05:00",
                        "onset": "2024-03-15T18:00:00-05:00",
                        "ends": "2024-03-16T06:00:00-05:00",
                        "headline": "Flood Warning issued March 15 at 6:00PM CDT until March 16 at 6:00AM CDT by NWS Austin/San Antonio",
                        "description": "The National Weather Service in Austin San Antonio has issued a Flood Warning for the following rivers in Texas...",
                        "instruction": "Motorists should not attempt to drive around barricades or drive cars through flooded areas."
                    }
                }
            ]
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        nws = NationalWeatherService()
        test_location = GeographicLocation(
            latitude=30.27,
            longitude=-97.74,
            elevation=UnitQuantity(167.0, 'm')
        )

        result = nws._get_alerts_data_from_api(geographic_location=test_location)

        self.assertIsInstance(result, dict)
        self.assertEqual(result['type'], 'FeatureCollection')
        self.assertIn('features', result)
        self.assertEqual(len(result['features']), 1)
        
        # Verify correct URL was called
        mock_get.assert_called_once()
        actual_url = mock_get.call_args[0][0]
        self.assertIn(f'point={test_location.latitude},{test_location.longitude}', actual_url)
        self.assertIn('alerts/active', actual_url)
        return

    @patch('hi.apps.weather.weather_sources.nws.requests.get')
    def test_get_alerts_data_from_api_no_alerts(self, mock_get):
        """Test API response with no active alerts - HIGH VALUE for empty response handling."""
        # Mock API response with no alerts
        mock_response_data = {
            "type": "FeatureCollection",
            "title": "Current watches, warnings, and advisories for 30.27 N, 97.74 W",
            "updated": "2024-03-15T20:00:00Z",
            "features": []
        }

        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        nws = NationalWeatherService()
        test_location = GeographicLocation(
            latitude=30.27,
            longitude=-97.74,
            elevation=UnitQuantity(167.0, 'm')
        )

        result = nws.get_weather_alerts(geographic_location=test_location)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
        return

    def test_parse_alerts_data_success(self):
        """Test successful parsing of weather alerts - HIGH VALUE for alert field mapping."""
        nws = NationalWeatherService()
        test_location = GeographicLocation(
            latitude=30.27,
            longitude=-97.74,
            elevation=UnitQuantity(167.0, 'm')
        )

        # Valid alerts API response
        alerts_data = {
            "features": [
                {
                    "properties": {
                        "event": "Tornado Warning",
                        "status": "Actual",
                        "category": "Met",
                        "severity": "Extreme",
                        "certainty": "Observed",
                        "urgency": "Immediate",
                        "headline": "Tornado Warning issued March 15 at 8:00PM CDT",
                        "description": "At 800 PM CDT, a severe thunderstorm capable of producing a tornado was located...",
                        "instruction": "TAKE COVER NOW! Move to a basement or an interior room on the lowest floor of a sturdy building.",
                        "areaDesc": "Travis County",
                        "effective": "2024-03-15T20:00:00-05:00",
                        "expires": "2024-03-15T20:30:00-05:00",
                        "onset": "2024-03-15T20:00:00-05:00",
                        "ends": "2024-03-15T20:30:00-05:00"
                    }
                }
            ]
        }

        result = nws._parse_alerts_data(
            alerts_data=alerts_data,
            geographic_location=test_location
        )

        # Verify result structure
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        
        alert = result[0]
        self.assertIsInstance(alert, WeatherAlert)
        
        # Verify alert fields
        self.assertEqual(alert.event_type, WeatherEventType.TORNADO)  # Should map from event name fallback
        self.assertEqual(alert.event, "Tornado Warning")
        self.assertEqual(alert.status, AlertStatus.ACTUAL)
        self.assertEqual(alert.category, AlertCategory.METEOROLOGICAL)
        self.assertEqual(alert.severity, AlertSeverity.EXTREME)
        self.assertEqual(alert.certainty, AlertCertainty.OBSERVED)
        self.assertEqual(alert.urgency, AlertUrgency.IMMEDIATE)
        self.assertEqual(alert.headline, "Tornado Warning issued March 15 at 8:00PM CDT")
        self.assertIn("severe thunderstorm", alert.description)
        self.assertIn("TAKE COVER NOW", alert.instruction)
        self.assertEqual(alert.affected_areas, "Travis County")
        
        # Verify timestamps are datetime objects
        self.assertIsInstance(alert.effective, datetime)
        self.assertIsInstance(alert.expires, datetime)
        self.assertIsInstance(alert.onset, datetime)
        self.assertIsInstance(alert.ends, datetime)
        return

    def test_parse_alerts_data_with_event_code(self):
        """Test parsing alerts with eventCode field - HIGH VALUE for canonical event type mapping."""
        nws = NationalWeatherService()
        test_location = GeographicLocation(
            latitude=30.27,
            longitude=-97.74,
            elevation=UnitQuantity(167.0, 'm')
        )

        # API response with eventCode field (like Lake Wind Advisory example)
        alerts_data = {
            "features": [
                {
                    "properties": {
                        "event": "Lake Wind Advisory",
                        "status": "Actual",
                        "category": "Met",
                        "severity": "Moderate",
                        "certainty": "Likely",
                        "urgency": "Expected",
                        "headline": "Lake Wind Advisory issued until 9:00PM MDT",
                        "description": "Southwest winds 10 to 20 mph with gusts up to 30 mph expected.",
                        "instruction": "Boaters on area lakes should use extra caution.",
                        "areaDesc": "Flathead/Mission Valleys",
                        "effective": "2024-03-15T12:00:00-06:00",
                        "expires": "2024-03-15T21:00:00-06:00",
                        "eventCode": {
                            "SAME": ["NWS"],
                            "NationalWeatherService": ["LWY"]
                        }
                    }
                }
            ]
        }

        result = nws._parse_alerts_data(
            alerts_data=alerts_data,
            geographic_location=test_location
        )

        # Verify result structure
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        
        alert = result[0]
        self.assertIsInstance(alert, WeatherAlert)
        
        # Verify event type mapping from NWS code
        self.assertEqual(alert.event_type, WeatherEventType.MARINE_WEATHER)  # LWY maps to MARINE_WEATHER
        self.assertEqual(alert.event, "Lake Wind Advisory")
        self.assertEqual(alert.status, AlertStatus.ACTUAL)
        self.assertEqual(alert.severity, AlertSeverity.MODERATE)
        return

    def test_parse_alerts_data_partial_fields(self):
        """Test parsing alerts with some missing fields - HIGH VALUE for robustness."""
        nws = NationalWeatherService()
        test_location = GeographicLocation(
            latitude=30.27,
            longitude=-97.74,
            elevation=UnitQuantity(167.0, 'm')
        )

        # API response with only some fields
        alerts_data = {
            "features": [
                {
                    "properties": {
                        "event": "Heat Advisory",
                        "status": "Actual",
                        "severity": "Minor",
                        "headline": "Heat Advisory in effect",
                        "effective": "2024-03-15T12:00:00-05:00",
                        "expires": "2024-03-15T20:00:00-05:00",
                        # Missing: certainty, urgency, description, instruction, etc.
                    }
                }
            ]
        }

        result = nws._parse_alerts_data(
            alerts_data=alerts_data,
            geographic_location=test_location
        )

        # Should succeed with defaults for missing fields
        self.assertEqual(len(result), 1)
        alert = result[0]
        
        self.assertEqual(alert.event, "Heat Advisory")
        self.assertEqual(alert.status, AlertStatus.ACTUAL)
        self.assertEqual(alert.severity, AlertSeverity.MINOR)
        # Should use defaults for missing fields
        self.assertEqual(alert.certainty, AlertCertainty.POSSIBLE)
        self.assertEqual(alert.urgency, AlertUrgency.UNKNOWN)
        self.assertEqual(alert.category, AlertCategory.METEOROLOGICAL)
        return

    def test_parse_iso_datetime_formats(self):
        """Test ISO datetime parsing with various formats - HIGH VALUE for timestamp handling."""
        nws = NationalWeatherService()
        
        test_cases = [
            ("2024-03-15T20:00:00-05:00", datetime),  # Standard ISO with timezone
            ("2024-03-15T20:00:00Z", datetime),       # UTC format
            ("2024-03-15T20:00:00", datetime),        # No timezone
            ("", None),                               # Empty string
            (None, None),                             # None input
        ]

        for iso_string, expected_type in test_cases:
            result = nws._parse_iso_datetime(iso_string)
            if expected_type is None:
                self.assertIsNone(result, f"Failed for: {iso_string}")
            else:
                self.assertIsInstance(result, expected_type, f"Failed for: {iso_string}")
        return

    def test_alerts_caching(self):
        """Test Redis caching behavior for alerts - HIGH VALUE for performance."""
        nws = NationalWeatherService()
        test_location = GeographicLocation(
            latitude=30.27,
            longitude=-97.74,
            elevation=UnitQuantity(167.0, 'm')
        )
        
        cache_key = f'ws:nws:alerts:{test_location.latitude:.3f}:{test_location.longitude:.3f}'
        
        # Mock cached data
        cached_alerts_data = {
            "features": [
                {
                    "properties": {
                        "event": "Cached Alert",
                        "status": "Actual",
                        "severity": "Minor",
                        "effective": "2024-03-15T12:00:00-05:00",
                        "expires": "2024-03-15T20:00:00-05:00"
                    }
                }
            ]
        }
        
        # Mock Redis client
        with patch.object(nws, '_redis_client') as mock_redis, \
             patch.object(nws, '_get_alerts_data_from_api') as mock_api_call:
            
            import json
            mock_redis.get.return_value = json.dumps(cached_alerts_data)
            
            result = nws._get_alerts_data(geographic_location=test_location)
            
            # Verify cache was checked and API was not called
            mock_redis.get.assert_called_once_with(cache_key)
            mock_api_call.assert_not_called()
            self.assertEqual(result, cached_alerts_data)
        return

    @patch('hi.apps.weather.weather_sources.nws.NationalWeatherService.get_weather_alerts')
    async def test_get_data_calls_alerts_method(self, mock_get_weather_alerts):
        """Test that get_data calls the weather alerts method - HIGH VALUE for integration."""
        # Mock weather manager
        mock_weather_manager = Mock()
        mock_weather_manager.update_current_conditions = Mock()
        mock_weather_manager.update_hourly_forecast = Mock()
        mock_weather_manager.update_daily_forecast = Mock()
        mock_weather_manager.update_weather_alerts = Mock()
        
        nws = NationalWeatherService()
        test_location = GeographicLocation(
            latitude=30.27,
            longitude=-97.74,
            elevation=UnitQuantity(167.0, 'm')
        )
        
        with patch.object(type(nws), 'geographic_location', new_callable=lambda: property(lambda self: test_location)), \
             patch.object(nws, 'weather_manager_async', return_value=mock_weather_manager), \
             patch.object(nws, 'get_current_conditions', return_value=None), \
             patch.object(nws, 'get_forecast_hourly', return_value=None), \
             patch.object(nws, 'get_forecast_12h', return_value=None):
            
            # Mock successful alerts
            mock_alerts = [
                WeatherAlert(
                    event_type=WeatherEventType.SEVERE_THUNDERSTORM,
                    event="Test Alert",
                    status=AlertStatus.ACTUAL,
                    category=AlertCategory.METEOROLOGICAL,
                    headline="Test Headline",
                    description="Test Description",
                    instruction="Test Instruction",
                    affected_areas="Test Area",
                    effective=datetime(2024, 3, 15, 20, 0, 0),
                    onset=datetime(2024, 3, 15, 20, 0, 0),
                    expires=datetime(2024, 3, 15, 23, 0, 0),
                    ends=datetime(2024, 3, 15, 23, 0, 0),
                    severity=AlertSeverity.MODERATE,
                    certainty=AlertCertainty.LIKELY,
                    urgency=AlertUrgency.EXPECTED,
                )
            ]
            mock_get_weather_alerts.return_value = mock_alerts
            
            # Call get_data
            await nws.get_data()
            
            # Verify alerts method was called
            mock_get_weather_alerts.assert_called_once_with(
                geographic_location=test_location
            )
            
            # Verify weather manager was called with alerts
            mock_weather_manager.update_weather_alerts.assert_called_once_with(
                weather_data_source=nws,
                weather_alerts=mock_alerts
            )
        return
            
        
