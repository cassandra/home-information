"""Short display labels for a set of sibling EntityStates.

States imported from an integration usually share their device's name
as a prefix (e.g., "EZFlora Front Lawn", "EZFlora Back Lawn"). Where
the states are shown together, such as in pairing UI, that prefix is
noise, so it is removed at a word boundary."""

from os.path import commonprefix
from typing import Dict, Sequence

from .models import EntityState


def entity_state_short_labels( entity_states : Sequence[ EntityState ] ) -> Dict[ int, str ]:
    """Map each EntityState id to its name without the leading words
    shared by all of the states. A state whose name would be left
    empty keeps its full name."""
    names = [ entity_state.name for entity_state in entity_states ]
    prefix = commonprefix( names ) if len( names ) > 1 else ''
    prefix = prefix[ : prefix.rfind( ' ' ) + 1 ]
    return {
        entity_state.id: entity_state.name[ len( prefix ): ].strip() or entity_state.name
        for entity_state in entity_states
    }
