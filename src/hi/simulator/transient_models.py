from dataclasses import dataclass, fields, asdict
from typing import List

from hi.apps.entity.enums import EntityType, EntityStateType

from .models import DbSimEntity


@dataclass
class SimState:

    db_id              : str
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
    

@dataclass
class SimEntity:
    """
    Base class that simulators will extend to add any defaults or new fields
    that need to defined for a specific simulator entity.  Simulators
    should define one or more subclasses and make those known to te
    SimulatorManager through the get_sim_entity_class_list() method of the
    Simulator class.

    The companion database DbSimEntity is used to persist the defined
    entities with conversions (below) between the two models.  This class
    is view of the database model that concerns the simulators themselves
    and not the extra concerns of the SimulatorManager (e.g.., SimProfile).
    """
    db_id           : int
    name            : str
    sim_state_list  : List[ SimState ]  # Simulators populate this as these are added (not persisted)
    entity_type     : EntityType

    def validate(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, field.type):
                raise TypeError( f'Field {field.name} must be type {field.type}, got {type(value).__name__}' )
            continue
        return

    def to_db_model( self ) -> DbSimEntity:
        """
        Creates a partially filled out DbSimEntity model from the
        entity-specific fields. The SimulatorManager will fill out the
        remaining DB fields (those others do not concern simulators).
        """
        base_field_names = { f.name for f in fields(SimEntity) }
        extra_fields = { k: v for k, v in asdict(self).items() if k not in base_field_names }
        
        return DbSimEntity(
            name = self.name,
            entity_type_str = str(self.entity_type),
            extra_fields = extra_fields,
        )

    @classmethod
    def from_db_model( cls, db_sim_entity : DbSimEntity ):
        data = {
            'db_id': db_sim_entity.id,
            'name': db_sim_entity.name,
            'entity_type': db_sim_entity.entity_type,
        }
        data.update( db_sim_entity.extra_fields )
        return cls( **data )
