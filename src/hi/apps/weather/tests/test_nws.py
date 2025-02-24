from datetime import datetime
import logging

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.weather.enums import (
    WeatherPhenomenon,
    WeatherPhenomenonIntensity,
    WeatherPhenomenonModifier,
)
from hi.apps.weather.transient_models import (
    NotablePhenomenon,
    NumericDataPoint,
    StringDataPoint,
    WeatherConditionsData,
)
from hi.apps.weather.weather_sources.nws import NationalWeatherService
from hi.units import UnitQuantity

from hi.tests.base_test_case import BaseTestCase


logging.disable(logging.CRITICAL)


class TestNationalWeatherService( BaseTestCase ):

    def test_parse_nws_quantity__exceptions(self):
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
        nws = NationalWeatherService()
        for nws_data_dict in test_data_list:
            with self.assertRaises( ValueError ):
                nws._parse_nws_quantity( nws_data_dict = nws_data_dict )
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

        nws = NationalWeatherService()

        for test_data in test_data_list:
            result_quantity = nws._parse_nws_quantity( nws_data_dict = test_data['nws_data_dict'])
            self.assertAlmostEqual( test_data['expected'].magnitude, result_quantity.magnitude, 3, test_data )
            self.assertEqual( test_data['expected'].units, result_quantity.units, test_data )
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
        elevation = UnitQuantity( 2, 'meters' )

        nws = NationalWeatherService()
        for nws_data_dict in test_data_list:
            result_data_point = nws._create_numeric_data_point(
                nws_data_dict = nws_data_dict,
                source_datetime = now,
                elevation = elevation,
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
        elevation = UnitQuantity( 2, 'meters' )

        nws = NationalWeatherService()

        for test_data in test_data_list:
            result_data_point = nws._create_numeric_data_point(
                nws_data_dict = test_data['nws_data_dict'],
                source_datetime = now,
                elevation = elevation,
            )
            self.assertEqual( nws.data_source, result_data_point.source )
            self.assertEqual( now, result_data_point.source_datetime )
            self.assertEqual( elevation, result_data_point.elevation )
            result_quantity = result_data_point.quantity
            self.assertAlmostEqual( test_data['expected'].magnitude, result_quantity.magnitude, 3, test_data )
            self.assertEqual( test_data['expected'].units, result_quantity.units, test_data )
            continue
        return

    def test_parse_cloud_layers(self):
        source_datetime = datetimeproxy.now()
        elevation = UnitQuantity( 2, 'meters' )
        nws = NationalWeatherService()

        test_data_list = [
            {
                'label': 'No Reported Cloud Layers (Empty List)',
                'properties': {
                    "cloudLayers": []
                },
                'expected_cloud_ceiling': None,
                'expected_cloud_cover': NumericDataPoint(
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 0, 'percent' ),
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
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 0, 'percent' ),
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
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 25, 'percent' ),
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
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 50, 'percent' ),
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
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 8000, 'feet' ),
                )    ,
                'expected_cloud_cover': NumericDataPoint(
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 87.5, 'percent' ),
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
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 12000, 'feet' ),
                )    ,
                'expected_cloud_cover': NumericDataPoint(
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 100, 'percent' ),
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
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 300, 'feet' ),
                )    ,
                'expected_cloud_cover': NumericDataPoint(
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 100, 'percent' ),
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
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 10000, 'feet' ),
                )    ,
                'expected_cloud_cover': NumericDataPoint(
                    source = nws.data_source,
                    source_datetime = source_datetime,
                    elevation = elevation,
                    quantity = UnitQuantity( 100, 'percent' ),
                ),
            },
        ]

        for test_data in test_data_list:
            weather_conditions_data = WeatherConditionsData()
            
            nws._parse_cloud_layers(
                properties = test_data['properties'],
                weather_conditions_data = weather_conditions_data,
                source_datetime =source_datetime,
                elevation = elevation,
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
        elevation = UnitQuantity( 2, 'meters' )
        nws = NationalWeatherService()

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
                properties = test_data['properties'],
                weather_conditions_data = weather_conditions_data,
                source_datetime =source_datetime,
                elevation = elevation,
            )

            expected_list = test_data['expected_list']
            result_list = weather_conditions_data.notable_phenomenon_list
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
            continue
        return
    
    def test_parse_observations_data(self):
        nws = NationalWeatherService()
        timestamp_str = '2025-02-20T04:51:00+00:00'
        source_datetime = datetime.fromisoformat( timestamp_str )
        elevation = UnitQuantity( 198, 'meters' )
        description = 'Cloudy'
        
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
                        "textDescription": description,
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
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( 103420, 'Pa' ),
                    ),
                    dew_point = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( -9.4, 'degC' ),
                    ),
                    heat_index = None,
                    temperature_max_last_24h = None,
                    temperature_min_last_24h = None,
                    precipitation_last_3h = None,
                    precipitation_last_6h = None,
                    precipitation_last_hour = None,
                    relative_humidity = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( 65.595209439964, 'percent' ),
                    ),
                    sea_level_pressure = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( 103580, 'Pa' ),
                    ),
                    temperature = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( -3.9, 'degC' ),
                    ),
                    visibility = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( 16090, 'meters' ),
                    ),
                    wind_chill = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( -7.757550390365555, 'degC' ),
                    ),
                    wind_direction = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( 350, 'degrees' ),
                    ),
                    windspeed_max = None,
                    windspeed_ave = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( 9.36, 'km / h' ),
                    ),
                    description = StringDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        value = description,
                    ),
                    cloud_ceiling = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( 880, 'meters' ),
                    ),
                    cloud_cover = NumericDataPoint(
                        source = nws.data_source,
                        source_datetime = source_datetime,
                        elevation = elevation,
                        quantity = UnitQuantity( 100, 'percent' ),
                    ),
                    notable_phenomenon_list = [],
                )
            }
        ]        

        def compare_numeric_data_point( expected, result, label ):
            if expected is None:
                self.assertIsNone( result, label )
                return
            
            self.assertEqual( expected.source, result.source, label )
            self.assertEqual( expected.source_datetime, result.source_datetime, label )
            self.assertEqual( expected.elevation, result.elevation, label )
            self.assertAlmostEqual( expected.quantity.magnitude, result.quantity.magnitude, 3, label )
            self.assertEqual( expected.quantity.units, result.quantity.units, label )
            return
            
        for test_data in test_data_list:
            expected = test_data['expected']
            result = nws._parse_observation_data( test_data['response'] )

            compare_numeric_data_point( expected.barometric_pressure,
                                        result.barometric_pressure,
                                        test_data['label']  )
            compare_numeric_data_point( expected.dew_point,
                                        result.dew_point,
                                        test_data['label']  )
            compare_numeric_data_point( expected.heat_index,
                                        result.heat_index,
                                        test_data['label'] )
            compare_numeric_data_point( expected.temperature_max_last_24h,
                                        result.temperature_max_last_24h,
                                        test_data['label']  )
            compare_numeric_data_point( expected.temperature_min_last_24h,
                                        result.temperature_min_last_24h,
                                        test_data['label']  )
            compare_numeric_data_point( expected.precipitation_last_3h,
                                        result.precipitation_last_3h,
                                        test_data['label']  )
            compare_numeric_data_point( expected.precipitation_last_6h,
                                        result.precipitation_last_6h,
                                        test_data['label']  )
            compare_numeric_data_point( expected.precipitation_last_hour,
                                        result.precipitation_last_hour,
                                        test_data['label']  )
            compare_numeric_data_point( expected.relative_humidity,
                                        result.relative_humidity,
                                        test_data['label']  )
            compare_numeric_data_point( expected.sea_level_pressure,
                                        result.sea_level_pressure,
                                        test_data['label']  )
            compare_numeric_data_point( expected.temperature,
                                        result.temperature,
                                        test_data['label']  )
            compare_numeric_data_point( expected.visibility,
                                        result.visibility,
                                        test_data['label']  )
            compare_numeric_data_point( expected.wind_chill,
                                        result.wind_chill,
                                        test_data['label']  )
            compare_numeric_data_point( expected.wind_direction,
                                        result.wind_direction,
                                        test_data['label']  )
            compare_numeric_data_point( expected.windspeed_max,
                                        result.windspeed_max,
                                        test_data['label']  )
            compare_numeric_data_point( expected.windspeed_ave,
                                        result.windspeed_ave,
                                        test_data['label']  )
            compare_numeric_data_point( expected.cloud_ceiling,
                                        result.cloud_ceiling,
                                        test_data['label']  )
            compare_numeric_data_point( expected.cloud_cover,
                                        result.cloud_cover,
                                        test_data['label']  )

            self.assertEqual( expected.description.value,
                              result.description.value,
                              test_data['label']  )

            self.assertEqual( len(expected.notable_phenomenon_list),
                              len(result.notable_phenomenon_list),
                              test_data['label']  )

            for expected_phenomenon, result_phenomenon in zip( expected.notable_phenomenon_list,
                                                               result.notable_phenomenon_list ):
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
            continue
        return
