"""
Authoring guidance: ``docs/dev/frontend/entity-state-panels.md``.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from hi.apps.entity.enums import DisplayContext, EntityStateRole, EntityType


@dataclass
class EntityStatePanel:

    name             : str
    display_contexts : Set[ DisplayContext ]
    priority         : int  # Priority 1 higher than priority 2
    template_name    : str

    entity_type      : Optional[ EntityType ]    = None  # If 'None' then used as fallback
    required_roles   : Set[ EntityStateRole ]    = field( default_factory = set )
    optional_roles   : Set[ EntityStateRole ]    = field( default_factory = set )
    # Each entry binds a template-context variable name (key) to one of
    # the panel's declared EntityStateRoles. The dispatcher resolves
    # these against ``state_status_data_by_role`` at render time so the
    # template can use ``{{ current_data.entity_state.id }}`` directly
    # instead of chaining ``{% with %}`` blocks. Aliases must reference
    # roles in ``required_roles | optional_roles``; absent optional
    # roles resolve to ``None``.
    role_data_template_aliases : Dict[ str, EntityStateRole ] = field( default_factory = dict )

    def __post_init__( self ):
        prefix = f'EntityStatePanel({self.name!r})'
        if not self.name or not isinstance( self.name, str ):
            raise TypeError( f'{prefix}: name must be a non-empty str' )
        if not self.template_name or not isinstance( self.template_name, str ):
            raise TypeError( f'{prefix}: template_name must be a non-empty str' )
        if not self.display_contexts:
            raise TypeError(
                f'{prefix}: display_contexts must be a non-empty Set[ DisplayContext ]'
            )
        for ctx in self.display_contexts:
            if not isinstance( ctx, DisplayContext ):
                raise TypeError(
                    f'{prefix}: display_contexts entries must be '
                    f'DisplayContext members; got {ctx!r}'
                )
        if not isinstance( self.priority, int ):
            raise TypeError( f'{prefix}: priority must be an int' )
        if self.entity_type is not None and not isinstance( self.entity_type, EntityType ):
            raise TypeError(
                f'{prefix}: entity_type must be an EntityType member or None'
            )
        overlap = self.required_roles & self.optional_roles
        if overlap:
            names = ', '.join( sorted( r.name for r in overlap ) )
            raise TypeError(
                f'{prefix}: required_roles and optional_roles must be disjoint; '
                f'overlap: {names}'
            )
        declared = self.required_roles | self.optional_roles
        for alias, role in self.role_data_template_aliases.items():
            if not isinstance( role, EntityStateRole ):
                raise TypeError(
                    f'{prefix}: role_data_template_aliases[{alias!r}] must be an '
                    f'EntityStateRole member; got {role!r}'
                )
            if role not in declared:
                raise TypeError(
                    f'{prefix}: role_data_template_aliases[{alias!r}] -> {role.name} '
                    f'is not in required_roles or optional_roles'
                )
        return
