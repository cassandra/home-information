from enum import Enum


class LabeledEnum(Enum):

    def __new__(cls, *args, **kwds):
        """ Adds auto-numbering """
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj
    
    def __init__( self, label : str, description : str ):
        self.label = label
        self.description = description
        return

    @classmethod
    def all(cls):
        return [ x for x in cls ]
    
    @classmethod
    def choices(cls):
        choice_list = list()
        for labeled_enum in cls:
            choice_list.append( ( labeled_enum.name.lower(), labeled_enum.label ) )
            continue
        return choice_list

    @classmethod
    def choices_or_none(cls):
        choice_list = [( '_none_', 'Any' )]
        choice_list.extend( cls.choices() )
        return choice_list

    @classmethod
    def int_choices(cls):
        return [ ( x.value, x.label ) for x in cls]    
    
    @classmethod
    def default(cls):
        """ Subclasses can override, else first item """
        return next(iter(cls))

    @classmethod
    def default_value(cls):
        return cls.default().name.lower()

    @classmethod
    def from_name( cls, name : str ):
        if name == '_none_':
            return None
        if name:
            for value in cls:
                if value.name.lower() == name.strip().lower():
                    return value
                continue
        raise ValueError( f'Unknown name value "{name}" for {cls.__name__}' )

    @classmethod
    def from_name_safe( cls, name : str ):
        try:
            return cls.from_name( name )
        except ValueError:
            return cls.default()

    @classmethod
    def from_value( cls, value : int ):
        for item in cls:
            if item.value == value:
                return item
            continue
        raise ValueError( f'Unknown value "{value}" for {cls.__name__}' )

    @classmethod
    def from_value_safe( cls, name : str ):
        try:
            return cls.from_value( name )
        except ValueError:
            return cls.default()

    @classmethod
    def to_dict_list(cls):
        dict_list = list()
        for item in cls:
            dict_list.append( item.to_dict() )
            continue
        return dict_list

    def to_dict(self):
        return {
            'value': self.name,
            'label': self.label,
            'description': self.description,
        }
    
    def __str__(self):
        return self.name.lower()
    
    def __int__(self):
        return self.value
    
    def url_name(self):
        return str(self)
    
    
class Platform(LabeledEnum):

    # IMPORTANT! These need to be in sync with Flutter App.
    #
    # See: flutterapp/lib/common/utils.dart:getPlatformString()
    
    UNKNOWN  = ( 'Unknown'   , '' )
    ANDROID  = ( 'Android'   , '' )
    IOS      = ( 'iOS'   , '' )
    LINUX    = ( 'GNU/Linux'   , '' )
    MACOS    = ( 'MacOS'   , '' )
    WINDOWS  = ( 'Windows'   , '' )
    OTHER    = ( 'Other'   , '' )
    
    @classmethod
    def default(cls):
        return cls.UNKNOWN

    @property
    def is_mobile(self):
        return self in [ Platform.ANDROID, Platform.IOS ]

    @property
    def is_ios(self):
        return bool( self == Platform.IOS )

    @property
    def is_android(self):
        return bool( self == Platform.ANDROID )
