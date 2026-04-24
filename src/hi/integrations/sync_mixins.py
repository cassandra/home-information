"""
Mixins for integration synchronization operations.

This module provides common functionality for integration sync operations,
particularly around intelligent entity deletion that preserves user data.
"""

import logging

from hi.apps.common.processing_result import ProcessingResult
from hi.apps.entity.models import Entity

from .entity_operations import EntityIntegrationOperations
from .user_data_detector import EntityUserDataDetector

logger = logging.getLogger(__name__)


class IntegrationSyncMixin:
    """
    Mixin providing common functionality for integration synchronization operations.

    Provides intelligent entity deletion that preserves user-created data
    while removing integration-specific components.
    """

    def _remove_entity_intelligently(self,
                                     entity: Entity,
                                     result: ProcessingResult,
                                     integration_name: str):
        """
        Remove an entity that no longer exists in the integration.

        If the entity has user-created attributes, preserve the entity but
        disconnect it from the integration and remove only integration-related
        components. Otherwise, perform complete deletion.
        """
        if EntityUserDataDetector.has_user_created_attributes(entity):
            EntityIntegrationOperations.preserve_with_user_data(
                entity = entity,
                integration_name = integration_name,
                result = result,
            )
        else:
            # No user data, safe to delete completely
            entity.delete()  # Deletion cascades to all related data
            result.message_list.append(f'Removed stale {integration_name} entity: {entity}')
