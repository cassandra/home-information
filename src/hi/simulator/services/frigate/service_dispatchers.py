"""Frigate simulator service dispatcher.

Scaffolding stub. The shape mirrors ``HassServiceDispatcher`` /
``ZoneMinder``'s monitor parameter setter: the simulator's incoming
API requests (e.g., camera detect-on / detect-off) dispatch to a
per-(sim_entity_fields_class) handler that translates the wire call
into SimState updates.

Feature work registers handlers in ``HassServiceDispatcher`` style:

    HassServiceDispatcher._REGISTRY = {
        FrigateCameraSimEntityFields: _camera,
        ...
    }
"""
import logging
from typing import Any, Dict, List, Tuple


logger = logging.getLogger(__name__)


class FrigateServiceDispatcher:
    """Routes simulator-side API service calls onto the right per-class
    handler. Empty registry for v0 scaffolding.
    """

    _REGISTRY: Dict = {}

    @classmethod
    def dispatch( cls,
                  sim_entity,
                  operation_name : str,
                  payload        : Dict[ str, Any ] ) -> List[ Tuple[ str, str ] ]:
        """Resolve to the per-(fields_class) handler. Returns a list
        of ``(sim_state_id, new_value)`` tuples describing the
        state changes implied by the call."""
        fields_class = sim_entity.sim_entity_fields.__class__
        handler = cls._REGISTRY.get( fields_class )
        if not handler:
            logger.debug(
                f'No Frigate service dispatcher for {fields_class.__name__}'
                f' op={operation_name}'
            )
            return []
        return handler(
            sim_entity = sim_entity,
            operation_name = operation_name,
            payload = payload,
        )
