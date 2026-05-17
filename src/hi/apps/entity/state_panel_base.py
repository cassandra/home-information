"""
Authoring guidance: ``docs/dev/frontend/entity-status-panels.md``.
"""

from dataclasses import dataclass, field
from typing import Optional, Set

from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType


@dataclass
class EntityStatusPanel:

    name             : str
    display_contexts : Set[ DisplayContext ]
    priority         : int  # Priority 1 higher than priority 2
    template_name    : str

    entity_type      : Optional[ EntityType ]   = None  # If 'None' then used as fallback
    required_roles   : Set[ EntityStateRole ]   = field( default_factory = set )
    optional_roles   : Set[ EntityStateRole ]   = field( default_factory = set )

    def __post_init__( self ):
        if not self.name or not isinstance( self.name, str ):
            raise TypeError(
                'EntityStatusPanel: name must be a non-empty str'
            )
        if not self.template_name or not isinstance( self.template_name, str ):
            raise TypeError(
                f'{self.name}: template_name must be a non-empty str'
            )
        if not self.display_contexts:
            raise TypeError(
                f'{self.name}: display_contexts must be a non-empty '
                f'Set[ DisplayContext ]'
            )
        for ctx in self.display_contexts:
            if not isinstance( ctx, DisplayContext ):
                raise TypeError(
                    f'{self.name}: display_contexts entries must be '
                    f'DisplayContext members; got {ctx!r}'
                )
        if not isinstance( self.priority, int ):
            raise TypeError(
                f'{self.name}: priority must be an int'
            )
        if self.entity_type is not None and not isinstance( self.entity_type, EntityType ):
            raise TypeError(
                f'{self.name}: entity_type must be an EntityType member or None'
            )
        overlap = self.required_roles & self.optional_roles
        if overlap:
            names = ', '.join( sorted( r.name for r in overlap ) )
            raise TypeError(
                f'{self.name}: required_roles and optional_roles must '
                f'be disjoint; overlap: {names}'
            )
        return
