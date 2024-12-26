from dataclasses import dataclass, fields, asdict, MISSING
from datetime import datetime
from typing import Any, Dict, List, Type

from hi.apps.entity.enums import EntityStateType, EntityType

from .models import DbSimEntity


@dataclass
class SimState:

    name               : str
    entity_state_type  : EntityStateType
    state_value        : str

    def validate(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, field.type):
                raise TypeError( f'Field {field.name} must be type {field.type}, got {type(value).__name__}' )
            continue
        return
    
    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict( cls, data ):
        return cls( **data )

    
@dataclass( frozen = True )
class SimEntity:
    """
    Base class that simulators extend to add any extra editable fields
    needed to define for a specific simulator entity.  Simulators should
    define one or more subclasses of this and make those known to te
    SimulatorManager through the get_sim_entity_class_list() method of the
    Simulator class.

    This class is the view of the model that concerns the Simulator
    instances themselves and not the extra concerns of the
    SimulatorManager.  The companion database model DbSimEntity is the
    SimulatorManager's view and is used to persist the defined entities
    with conversions (below) between the two models.
    """

    name             : str

    @classmethod
    def class_label(cls):
        raise NotImplementedError('Subclasses must override this method.')
    
    @classmethod
    def get_entity_type(cls) -> EntityType:
        raise NotImplementedError('Subclasses must override this method.')

    @property
    def sim_state_list(self) -> List[ SimState ]:
        """
        These are defined by the Simulator and used by the SimulatorManager to
        know what states exists and can be simulated.  The Simulator keeps track of
        the current value of these states as provided by the SimulatorManager by 
        way of the UI or a predefined simulation script.  These are not persisted.
        """
        raise NotImplementedError('Subclasses must override this method.')

    def to_json_dict(self) -> Dict[ str, Any ]:
        """
        Subclasses only need to override this if the field types are not
        directly JSON serializable or lack special cases defined in this
        method (e.g., datetime).
        """
        json_dict = dict()
        for field in fields(self):
            value = getattr( self, field.name )
            if isinstance( value, datetime ):
                value = value.isoformat()
            json_dict[field.name] = value
            continue
        return json_dict

    @classmethod
    def from_json_dict( cls, json_content : Dict[ str, Any ] ) -> 'SimEntity':
        """
        Subclasses only need to override this if the field types are not
        directly JSON deserializable or lack special cases defined in this
        method (e.g., datetime).
        """
        kwargs = dict()
        for field in fields( cls ):
            value = json_content.get( field.name, field.default )
            if ( field.type == datetime ) and isinstance( value, str ):
                value = datetime.fromisoformat( value )
            kwargs[field.name] = value
            continue
        return cls( **kwargs )

    def to_initial_form_values( self ) -> Dict[ str, Any ]:
        initial_values = dict()
        for field in fields(self):
            initial_values[field.name] = getattr( self, field.name )
            continue
        return initial_values

    @classmethod
    def from_form_data( cls, form_data : Dict[ str, Any ] ) -> 'SimEntity':
        kwargs = dict()
        for field in fields( cls ):
            value = form_data.get( field.name, field.default )
            if value is MISSING:
                value = None
            kwargs[field.name] = value
            continue
        return cls( **kwargs )


@dataclass
class SimEntityData:

    sim_entity       : SimEntity
    db_sim_entity    : DbSimEntity   = None 


@dataclass
class SimEntityClassData:

    sim_entity_class   : Type[ SimEntity ]

    @property
    def class_id(self) -> str:
        return f'{self.sim_entity_class.__module__}.{self.sim_entity_class.__qualname__}'

    @property
    def class_label(self) -> str:
        return self.sim_entity_class.class_label()

    @property
    def entity_type(self) -> EntityType:
        return self.sim_entity_class.get_entity_type()
