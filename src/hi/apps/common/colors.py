import colorsys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List
from typing import ClassVar


@dataclass
class Color:
    rgb_hex : str
    
    BLACK_RGB_HEX         : ClassVar  = '000000'
    WHITE_RGB_HEX         : ClassVar  = 'ffffff'
    ALMOST_BLACK_RGB_HEX  : ClassVar  = '0d0d0d'
    ALMOST_WHITE_RGB_HEX  : ClassVar  = 'fdfdfd'

    @property
    def on_rgb_hex(self):
        """ Returns an rgb hex string that can be used to display "on" the color (e.g., for text) """
        try:
            if self.luminance > 0.5:
                return self.ALMOST_BLACK_RGB_HEX
            return self.ALMOST_WHITE_RGB_HEX
        except ( TypeError, ValueError ):
            return self.ALMOST_BLACK_RGB_HEX

    @property
    def css_color(self):
        return f'#{self.rgb_hex}'
    
    @property
    def on_color(self):
        return Color( self.on_rgb_hex )

    @property
    def on_css_color(self):
        return f'#{self.on_rgb_hex}'

    @property
    def luminance(self):
        return self.rgb_hex_to_luminance( self.rgb_hex )
    
    def __str__(self):
        return self.rgb_hex

    def to_dict(self):
        return {
            'type': 'color',
            'rgb_hex': self.rgb_hex,
            'on_rgb_hex': self.on_rgb_hex,
        }
    
    @classmethod
    def rgb_hex_to_rgb( cls, rgb_hex : str ):
        """ RGB values range is 0.0 to 1.0 """
        r = int( rgb_hex[0:2], 16 ) / 255.0
        g = int( rgb_hex[2:4], 16 ) / 255.0
        b = int( rgb_hex[4:6], 16 ) / 255.0
        return ( r, g, b )
    
    @classmethod
    def rgb_hex_to_hsv( cls, rgb_hex : str ):
        ( r, g, b ) = cls.rgb_hex_to_rgb( rgb_hex )
        h, s, v = colorsys.rgb_to_hsv( r, g, b )
        return ( h, s, v )

    @classmethod
    def rgb_hex_to_luminance( cls, rgb_hex : str ):
        ( r, g, b ) = cls.rgb_hex_to_rgb( rgb_hex )
        return ( 0.299 * r + 0.587 * g + 0.114 * b )
    

class ColorHue(Enum):

    # Source: https://github.com/fchristant/colar/blob/master/colar/colar.js
    # Explanation: https://ferdychristant.com/color-for-the-color-challenged-884c7aa04a56

    def __new__(cls, *args, **kwds):
        """ Adds auto-numbering """
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj
    
    def __init__( self, label : str, luminosity_step_to_rgb_hex : Dict[ int, str ] ):
        self.label = label
        self.luminosity_step_to_rgb_hex = luminosity_step_to_rgb_hex
        return

    def steps_and_colors( self ):
        for step, rgb_hex in self.luminosity_step_to_rgb_hex.items():
            yield ( step, Color( rgb_hex = rgb_hex ) )
            continue
        return
        
    def __iter__(self):
        for rgb_hex in self.luminosity_step_to_rgb_hex.values():
            yield Color( rgb_hex = rgb_hex )
            continue
        return
    
    def __getitem__( self, key ):
        try:
            return self.__getattr__( key )
        except AttributeError:
            raise KeyError()
        
    def __getattr__( self, name : str ):
        try:
            luminosity_step = int(name)
            if luminosity_step < 0:
                luminosity_step = 0
            elif luminosity_step > 12:
                luminosity_step = 12
            return Color( rgb_hex = self.luminosity_step_to_rgb_hex[luminosity_step] )
        except (TypeError, ValueError):
            pass
        raise AttributeError()
        
    GRAY = (
        'Gray', {
            0: 'F8FAFB',
            1: 'F2F4F6',
            2: 'EBEDEF',
            3: 'E0E4E5',
            4: 'D1D6D8',
            5: 'B1B6B9',
            6: '979B9D',
            7: '7E8282',
            8: '666968',
            9: '50514F',
            10: '3A3A37',
            11: '252521',
            12: '121210',
        }
    )
    RED = (
        'Red', {
            0: 'FFF5F5',
            1: 'FFE3E3',
            2: 'FFC9C9',
            3: 'FFA8A8',
            4: 'FF8787',
            5: 'FF6B6B',
            6: 'FA5252',
            7: 'F03E3E',
            8: 'E03131',
            9: 'C92A2A',
            10: 'B02525',
            11: '962020',
            12: '7D1A1A',
        }
    )
    PINK = (
        'Pink', {
            0: 'FFF0F6',
            1: 'FFDEEB',
            2: 'FCC2D7',
            3: 'FAA2C1',
            4: 'F783AC',
            5: 'F06595',
            6: 'E64980',
            7: 'D6336C',
            8: 'C2255C',
            9: 'A61E4D',
            10: '8C1941',
            11: '731536',
            12: '59102A',
        }
    )
    PURPLE = (
        'Purple', {
            0: 'F8F0FC',
            1: 'F3D9FA',
            2: 'EEBEFA',
            3: 'E599F7',
            4: 'DA77F2',
            5: 'CC5DE8',
            6: 'BE4BDB',
            7: 'AE3EC9',
            8: '9C36B5',
            9: '862E9C',
            10: '702682',
            11: '5A1E69',
            12: '44174F',
        }
    )
    VIOLET = (
        'Violet', {
            0: 'F3F0FF',
            1: 'E5DBFF',
            2: 'D0BFFF',
            3: 'B197FC',
            4: '9775FA',
            5: '845EF7',
            6: '7950F2',
            7: '7048E8',
            8: '6741D9',
            9: '5F3DC4',
            10: '5235AB',
            11: '462D91',
            12: '3A2578',
        }
    )
    INDIGO = (
        'Indigo', {
            0: 'EDF2FF',
            1: 'DBE4FF',
            2: 'BAC8FF',
            3: '91A7FF',
            4: '748FFC',
            5: '5C7CFA',
            6: '4C6EF5',
            7: '4263EB',
            8: '3B5BDB',
            9: '364FC7',
            10: '2F44AD',
            11: '283A94',
            12: '21307A',
        }
    )
    BLUE = (
        'Blue', {
            0: 'E7F5FF',
            1: 'D0EBFF',
            2: 'A5D8FF',
            3: '74C0FC',
            4: '4DABF7',
            5: '339AF0',
            6: '228BE6',
            7: '1C7ED6',
            8: '1971C2',
            9: '1864AB',
            10: '145591',
            11: '114678',
            12: '0D375E',
        }
    )
    CYAN = (
        'Cyan', {
            0: 'E3FAFC',
            1: 'C5F6FA',
            2: '99E9F2',
            3: '66D9E8',
            4: '3BC9DB',
            5: '22B8CF',
            6: '15AABF',
            7: '1098AD',
            8: '0C8599',
            9: '0B7285',
            10: '095C6B',
            11: '074652',
            12: '053038',
        }
    )
    TEAL = (
        'Teal', {
            0: 'E6FCF5',
            1: 'C3FAE8',
            2: '96F2D7',
            3: '63E6BE',
            4: '38D9A9',
            5: '20C997',
            6: '12B886',
            7: '0CA678',
            8: '099268',
            9: '087F5B',
            10: '066649',
            11: '054D37',
            12: '033325',
        }
    )
    GREEN = (
        'Green', {
            0: 'EBFBEE',
            1: 'D3F9D8',
            2: 'B2F2BB',
            3: '8CE99A',
            4: '69DB7C',
            5: '51CF66',
            6: '40C057',
            7: '37B24D',
            8: '2F9E44',
            9: '2B8A3E',
            10: '237032',
            11: '1B5727',
            12: '133D1B',
        }
    )
    LIME = (
        'Lime', {
            0: 'F4FCE3',
            1: 'E9FAC8',
            2: 'D8F5A2',
            3: 'C0EB75',
            4: 'A9E34B',
            5: '94D82D',
            6: '82C91E',
            7: '74B816',
            8: '66A80F',
            9: '5C940D',
            10: '4C7A0B',
            11: '3C6109',
            12: '2C4706',
        }
    )
    YELLOW = (
        'Yellow', {
            0: 'FFF9DB',
            1: 'FFF3BF',
            2: 'FFEC99',
            3: 'FFE066',
            4: 'FFD43B',
            5: 'FCC419',
            6: 'FAB005',
            7: 'F59F00',
            8: 'F08C00',
            9: 'E67700',
            10: 'B35C00',
            11: '804200',
            12: '663500',
        }
    )
    ORANGE = (
        'Orange', {
            0: 'FFF4E6',
            1: 'FFE8CC',
            2: 'FFD8A8',
            3: 'FFC078',
            4: 'FFA94D',
            5: 'FF922B',
            6: 'FD7E14',
            7: 'F76707',
            8: 'E8590C',
            9: 'D9480F',
            10: 'BF400D',
            11: '99330B',
            12: '802B09',
        }
    )
    CHOCO = (
        'Choco', {
            0: 'FFF8DC',
            1: 'FCE1BC',
            2: 'F7CA9E',
            3: 'F1B280',
            4: 'E99B62',
            5: 'DF8545',
            6: 'D46E25',
            7: 'BD5F1B',
            8: 'A45117',
            9: '8A4513',
            10: '703A13',
            11: '572F12',
            12: '3D210D',
        }
    )
    BROWN = (
        'Brown', {
            0: 'FAF4EB',
            1: 'EDE0D1',
            2: 'E0CAB7',
            3: 'D3B79E',
            4: 'C5A285',
            5: 'B78F6D',
            6: 'A87C56',
            7: '956B47',
            8: '825B3A',
            9: '6F4B2D',
            10: '5E3A21',
            11: '4E2B15',
            12: '422412',
        }
    )
    SAND = (
        'Sand', {
            0: 'F8FAFB',
            1: 'E6E4DC',
            2: 'D5CFBD',
            3: 'C2B9A0',
            4: 'AEA58C',
            5: '9A9178',
            6: '867C65',
            7: '736A53',
            8: '5F5746',
            9: '4B4639',
            10: '38352D',
            11: '252521',
            12: '121210',
        }
    )
    CAMO = (
        'Camo', {
            0: 'F9FBE7',
            1: 'E8ED9C',
            2: 'D2DF4E',
            3: 'C2CE34',
            4: 'B5BB2E',
            5: 'A7A827',
            6: '999621',
            7: '8C851C',
            8: '7E7416',
            9: '6D6414',
            10: '5D5411',
            11: '4D460E',
            12: '36300A',
        }
    )
    JUNGLE = (
        'Jungle', {
            0: 'ECFEB0',
            1: 'DEF39A',
            2: 'D0E884',
            3: 'C2DD6E',
            4: 'B5D15B',
            5: 'A8C648',
            6: '9BBB36',
            7: '8FB024',
            8: '84A513',
            9: '7A9908',
            10: '658006',
            11: '516605',
            12: '3D4D04',
        }
    )

    # Tools used for WAA theme colors below:
    #
    #    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors
    #    https://coolors.co/
    #    https://www.tints.dev/blue/3B82F6
    
    WAA_PRIMARY = (
        'Waa Red', {
            0: 'FCEFF1',
            1: 'F4E7E9',
            2: 'E6C3C7',
            3: 'C68A8B',
            4: 'AE6062',
            5: 'B04242',
            6: 'AD302B',
            7: 'A02929',
            8: '902224',
            9: '821e1e',
            10: '721917',  # Base color (seed)
            11: '4C100F',
            12: '260808',
        }
    )

    WAA_SECONDARY = (
        'Waa Black', {
            0: 'ffffff',
            1: 'f5f5f8',
            2: 'eaeaed',
            3: 'dbdbde',
            4: 'c6c6c9',
            5: 'a0a0a3',
            6: '7e7e81',
            7: '58585a',
            8: '454548',
            9: '28282b',
            10: '040408',  # Base color (seed)
            11: '020206',
            12: '000000',
        }
    )

    WAA_TERTIARY = (
        'Waa Cyan', {
            0: 'EFFFFF',
            1: 'E2FAFC',
            2: 'B7F2F6',
            3: '89E9F2',
            4: '5BDFEC',
            5: '3BD7E7',
            6: '29D0E4',
            7: '26BFD1',
            8: '22A9B6',
            9: '1e949e',
            10: '177072',  # Base color (auto)
            11: '0F4B4C',
            12: '082626',
        }
    )

    WAA_SUCCESS = (
        'Waa Green', {
            0: 'FCFFF8',
            1: 'F0FAE9',
            2: 'D9F1C9',
            3: 'BFE7A6',
            4: 'A5DD81',
            5: '90D664',
            6: '7CCE48',
            7: '6DBD3F',
            8: '58A935',
            9: '43942c',
            10: '177219',  # Base color (auto)
            11: '0F4C10',
            12: '082608',
        }
    )

    WAA_WARNING = (
        'Waa Orange', {
            0: 'FFFAF8',
            1: 'F8EAE8',
            2: 'FACDC0',
            3: 'F8AD98',
            4: 'F68E70',
            5: 'F57551',
            6: 'F45F36',  # Base color (manual)
            7: 'E95932',
            8: 'DB532D',
            9: 'cd4c2a',
            10: 'B24224',
            11: '6F1D06',
            12: '3A0F03',
        }
    )
        
    WAA_ERROR = (
        'Waa Yellow', {
            0: 'FFFFF8',
            1: 'FCFDE6',
            2: 'F9F8C1',
            3: 'F5F398',
            4: 'F2EF6F',
            5: 'EEEA4D',
            6: 'EBE527',
            7: 'EDD521',
            8: 'EDBD14',
            9: 'ECA500',  # Base color (manual)
            10: 'EA7C00',
            11: '9E6F00',
            12: '4D3600',
        }
    )

      
class ColorPaletteType:
    """ For choosing how many luminosity steps you want for a color hue """
    THIRTEEN_STEP = 'thirteen_step'
    SEVEN_STEP = 'seven_step'
    FIVE_STEP = 'five_step'

    
class ColorPalette:

    def __init__( self, luminosity_step_list : List[ int ] ):

        self._color_hue_to_luminosity_step_to_colors = dict()
        for color_hue in ColorHue:
            luminosity_step_to_colors = {
                idx: color for idx, color in enumerate( color_hue )
                if idx in luminosity_step_list }
            self._color_hue_to_luminosity_step_to_colors[color_hue] = luminosity_step_to_colors
            continue
        
        return

    def hues(self):
        return [ x for x in self.self._color_hue_to_luminosity_step_to_colors.keys() ]

    def __iter__(self):
        for color_hue, luminosity_step_to_colors in self._color_hue_to_luminosity_step_to_colors.items():
            yield ( color_hue, luminosity_step_to_colors )
            continue
        return
    
    
class ColorPalette13Step( ColorPalette ):
    def __init__(self):
        super().__init__( luminosity_step_list = [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 ] )
        return

    
class ColorPalette7Step( ColorPalette ):
    def __init__(self):
        super().__init__( luminosity_step_list = [ 0, 2, 4, 6, 8, 10, 12 ] )
        return

    
class ColorPalette5Step( ColorPalette ):
    def __init__(self):
        super().__init__( luminosity_step_list = [ 0, 3, 6, 9, 12 ] )
        return

    
class RangedColor:

    def __init__( self,
                  color_hue          : ColorHue,
                  luminosity_step    : int ):
        self.color_hue = color_hue
        self.luminosity_step = luminosity_step

        self._color = color_hue[luminosity_step]
        try:
            self._color_lighter = color_hue[luminosity_step - 1]
        except KeyError:
            self._color_lighter = self._color
        try:
            self._color_lighter2 = color_hue[luminosity_step - 2]
        except KeyError:
            self._color_lighter2 = self._color_lighter
        try:
            self._color_lighter3 = color_hue[luminosity_step - 3]
        except KeyError:
            self._color_lighter3 = self._color_lighter2
        try:
            self._color_lighter4 = color_hue[luminosity_step - 4]
        except KeyError:
            self._color_lighter4 = self._color_lighter3
        try:
            self._color_darker = color_hue[luminosity_step + 1]
        except KeyError:
            self._color_darker = self._color
        try:
            self._color_darker2 = color_hue[luminosity_step + 2]
        except KeyError:
            self._color_darker2 = self._color_darker
        try:
            self._color_darker3 = color_hue[luminosity_step + 3]
        except KeyError:
            self._color_darker3 = self._color_darker2
        try:
            self._color_darker4 = color_hue[luminosity_step + 4]
        except KeyError:
            self._color_darker4 = self._color_darker3
        return

    @property
    def color(self):
        return self._color

    @property
    def on_color(self):
        return self._color.on_color

    @property
    def color_lighter(self):
        return self._color_lighter

    @property
    def color_lighter2(self):
        return self._color_lighter2    
    
    @property
    def color_lighter3(self):
        return self._color_lighter3    
    
    @property
    def color_lighter4(self):
        return self._color_lighter4    
    
    @property
    def color_darker(self):
        return self._color_darker

    @property
    def color_darker2(self):
        return self._color_darker2

    @property
    def color_darker3(self):
        return self._color_darker3

    @property
    def color_darker4(self):
        return self._color_darker4
