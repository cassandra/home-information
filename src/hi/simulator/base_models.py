from dataclasses import dataclass, fields, MISSING
from datetime import datetime
from typing import Any, Dict, List, Tuple, Type

from .enums import SimEntityType, SimStateType


@dataclass( frozen = True )
class SimEntityFields:
    """
    Base class that simulators should extend to add extra (editable) fields
    needed to define for a specific simulator entity.  Simulators should
    define one or more subclasses of this and make those known to the
    SimulatorManager through the sim_entity_definition_list() method of the
    Simulator class (using the SimEntityDefinition class).
    """
    name             : str
    
    @classmethod
    def class_id(cls) -> str:
        dotted_path = f'{cls.__module__}.{cls.__qualname__}'
        parts = dotted_path.split('.')
        return '.'.join( reversed( parts ))
    
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
    def from_json_dict( cls, json_content : Dict[ str, Any ] ) -> 'SimEntityFields':
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
    def from_form_data( cls, form_data : Dict[ str, Any ] ) -> 'SimEntityFields':
        kwargs = dict()
        for field in fields( cls ):
            value = form_data.get( field.name, field.default )
            if value is MISSING:
                value = None
            kwargs[field.name] = value
            continue
        return cls( **kwargs )


@dataclass
class SimState:
    """
    Base class that individual simulators should override to define the
    states for a simulator entity. A simulator entity will provide one or
    more SimState subclasses. SimState classes are provided via the
    SimEntityDefinition and will be initialized with the containing
    entities fields and values by the SimulatorManager.

    SimState definitions and instances are not persisted in the database.
    """

    # These fields are provided by SimulatorManager when creating instances.
    simulator_id       : str
    sim_entity_id      : int
    sim_state_idx      : int
    sim_entity_fields  : SimEntityFields

    # Subclasses must provide a default value for these.    
    sim_state_type     : SimStateType

    # Subclasses may provide a default value for this.    
    value              : Any              = None

    @property
    def name(self):
        return self.sim_entity_fields.name

    def set_value_from_string( self, value_str : str ):
        """ Subclasses should override this is the value is not a string and needs conversion. """
        self.value = value_str
        return
    
    @property
    def min_value(self) -> Any:
        """ Subclasses can override this to define the minimum valid value """
        return None
    
    @property
    def max_value(self) -> Any:
        """ Subclasses can override this to define the maximum valid value """
        return None
    
    @property
    def choices(self) -> List[ Tuple[ str, str ]]:
        """ Subclasses using SimStateType.DISCRETE should override this to provide the valid values. """
        return list()
    

@dataclass
class SimEntityDefinition:
    """
    Used by Simulator instances to define a simulated entity that is
    available to be defined and added to the simulator configuration.  Each
    type of simulated entity should also provide one or more SimState
    subclasses that will be used to track the state/status of the simulation.
    """
    
    class_label              : str
    sim_entity_type          : SimEntityType
    sim_entity_fields_class  : Type[ SimEntityFields ]
    sim_state_class_list     : List[ Type[ SimState ]]
    
    @property
    def class_id(self) -> str:
        return f'{self.sim_entity_fields_class.class_id()}'


    
