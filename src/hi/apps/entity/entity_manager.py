import logging
from threading import local
from typing import List, Sequence

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from hi.apps.common.singleton import Singleton
from hi.apps.location.models import LocationView

from .entity_pairing_manager import EntityPairingManager
from .entity_placement import EntityPlacer
from .enums import EntityGroupType
from .models import (
    Entity,
    EntityAttribute,
    EntityPath,
    EntityPosition,
    EntityState,
    EntityStateDelegation,
    EntityView,
)
from .transient_models import (
    EntityEditModeData,
    EntityViewGroup,
    EntityViewItem,
)

logger = logging.getLogger(__name__)


class EntityManager(Singleton):
    """Entity-domain coordination: edit-mode data assembly, view-group
    rendering, capability listings, and the change-listener registry.

    Initial entity placement, persistence of EntityPosition /
    EntityPath rows, and entity-type transitions all live in
    ``hi.apps.entity.entity_placement``."""

    def __init_singleton__(self):
        self._change_listeners = list()
        self.reload()
        return

    def reload(self):
        self._notify_change_listeners()
        return

    def register_change_listener( self, callback ):
        logger.debug( f'Adding EntityManager change listener from {callback.__module__}' )
        self._change_listeners.append( callback )
        return

    def _notify_change_listeners(self):
        for callback in self._change_listeners:
            try:
                callback()
            except Exception as e:
                logger.exception( 'Problem calling EntityManager change callback.', e )
            continue
        return

    def get_entity_edit_mode_data( self,
                                   entity         : Entity,
                                   location_view  : LocationView,
                                   is_editing     : bool )        -> EntityEditModeData:

        entity_position_form = None
        if is_editing:
            entity_position_form = EntityPlacer().get_entity_position_form(
                entity = entity,
                location_view = location_view,
            )

        entity_pairing_list = EntityPairingManager().get_entity_pairing_list( entity = entity )

        return EntityEditModeData(
            entity = entity,
            entity_position_form = entity_position_form,
            entity_pairing_list = entity_pairing_list,
        )

    def create_location_entity_view_group_list( self,
                                                location_view : LocationView,
                                                unused_entity_ids : set = None ) -> List[EntityViewGroup]:
        existing_entities = [ x.entity
                              for x in location_view.entity_views.select_related('entity').all() ]
        all_entities = Entity.objects.all()
        return self.create_entity_view_group_list(
            existing_entities = existing_entities,
            all_entities = all_entities,
            unused_entity_ids = unused_entity_ids,
        )

    def create_entity_view_group_list( self,
                                       existing_entities  : List[ Entity ],
                                       all_entities       : Sequence[ Entity ],
                                       unused_entity_ids  : set = None ) -> List[EntityViewGroup]:
        existing_entity_set = set( existing_entities )
        if unused_entity_ids is None:
            unused_entity_ids = set()

        entity_view_group_dict = dict()
        for entity in all_entities:
            entity_view_item = EntityViewItem(
                entity = entity,
                exists_in_view = bool( entity in existing_entity_set ),
                is_unused = entity.id in unused_entity_ids,
            )
            entity_group_type = EntityGroupType.from_entity_type( entity.entity_type )
            if entity_group_type not in entity_view_group_dict:
                entity_view_group = EntityViewGroup(
                    entity_group_type = entity_group_type,
                )
                entity_view_group_dict[entity_group_type] = entity_view_group
            entity_view_group_dict[entity_group_type].item_list.append( entity_view_item )
            continue

        for entity_group_type, entity_view_group in entity_view_group_dict.items():
            entity_view_group.item_list.sort( key = lambda item : item.entity.name )
            continue

        entity_view_group_list = list( entity_view_group_dict.values() )
        entity_view_group_list.sort( key = lambda item : item.entity_group_type.label )
        return entity_view_group_list

    def get_view_stream_entities(self) -> List[ Entity ]:
        """
        Return all entities that have a video-stream capability AND are
        not currently disabled. Both conditions are required for an entity
        to surface in capability-driven enumerations like the sidebar
        Cameras list. Per-entity view sites should keep using the raw
        has_video_stream flag — the disabled gate only applies at
        listing time.
        """
        return list(Entity.objects.filter(
            has_video_stream = True,
            is_disabled = False,
        ))


_thread_local = local()


def do_entity_manager_reload():
    logger.debug( 'Reloading EntityManager from model changes.')
    EntityManager().reload()
    _thread_local.reload_registered = False
    return


@receiver( post_save, sender = Entity )
@receiver( post_save, sender = EntityState )
@receiver( post_save, sender = EntityAttribute )
@receiver( post_save, sender = EntityStateDelegation )
@receiver( post_save, sender = EntityPosition )
@receiver( post_save, sender = EntityPath )
@receiver( post_save, sender = EntityView )
@receiver( post_delete, sender = Entity )
@receiver( post_delete, sender = EntityState )
@receiver( post_delete, sender = EntityAttribute )
@receiver( post_delete, sender = EntityStateDelegation )
@receiver( post_delete, sender = EntityPosition )
@receiver( post_delete, sender = EntityPath )
@receiver( post_delete, sender = EntityView )
def entity_manager_model_changed( sender, instance, **kwargs ):
    """
    Queue the EntityManager.reload() call to execute after the transaction
    is committed.  This prevents reloading multiple times if multiple
    models saved as part of a transaction.
    """
    if not hasattr(_thread_local, "reload_registered"):
        _thread_local.reload_registered = False

    logger.debug( 'EntityManager model change detected.')

    if not _thread_local.reload_registered:
        logger.debug( 'Queuing EntityManager reload on model change.')
        _thread_local.reload_registered = True
        transaction.on_commit( do_entity_manager_reload )

    return
