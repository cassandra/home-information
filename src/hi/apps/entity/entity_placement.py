"""
Entity placement: putting entities into LocationViews.

"Placement" is the union of (a) deciding what an entity should look
like in a view (a centered icon, a default path), (b) persisting the
chosen ``EntityPosition`` / ``EntityPath`` row, and (c) linking the
entity to the ``LocationView`` via an ``EntityView``. All three are
the responsibility of this module.

Two collaborating classes:

* ``EntityPlacementCalculator`` — orchestrates per-entity shape
  selection (Point vs Path), delegating "where in the SVG" to
  ``PositionGeometry`` and "how a path looks" to ``PathGeometry``.
  Performs no DB writes.

* ``EntityPlacer`` — DB-touching placer. Accepts either a
  pre-computed ``PlacementShape`` (e.g., from Phase 3's dispatcher
  modal that lays out an entire sync result group at once) or
  derives one via the calculator. Persists the result, links the
  entity to the view, manages delegates, owns un-place / toggle
  counterparts, and runs entity-type transitions.

Known limitation (carried over from earlier code, not introduced by
this module): when an entity carrying delegate entities is placed
into a view, the delegates are placed at the viewbox center
without any spread. Multiple delegates therefore overlap. Phase 3
inherits this behavior; revisit when it bites.
"""

from dataclasses import dataclass
from decimal import Decimal
import logging
from typing import List, Optional, Tuple, Union

from django.db import transaction

from hi.apps.entity.edit.forms import EntityPositionForm
from hi.apps.entity.enums import EntityTransitionType
from hi.apps.location.models import Location, LocationView
from hi.apps.location.path_geometry import PathGeometry
from hi.apps.location.position_geometry import PositionGeometry

from .entity_pairing_manager import EntityPairingManager
from .models import (
    Entity,
    EntityPath,
    EntityPosition,
    EntityView,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlacementPoint:
    """SVG icon placement: center-of-icon coordinates plus scale."""
    svg_x: float
    svg_y: float
    svg_scale: Decimal


@dataclass(frozen=True)
class PlacementPath:
    """SVG path placement: a fully-formed path string already centered
    and sized for the chosen view."""
    svg_path: str


PlacementShape = Union[PlacementPoint, PlacementPath]


class EntityPlacementCalculator:
    """Orchestrates per-entity shape selection. Pure-functional;
    performs no DB writes. The geometry math lives in
    ``PositionGeometry`` (where) and ``PathGeometry`` (how a path
    looks); this class branches on entity_type to decide which
    output shape applies.
    """

    def shape_for_entity( self,
                          entity         : Entity,
                          location_view  : LocationView ) -> PlacementShape:
        """Return the placement shape for a single entity centered on
        the current viewbox."""
        svg_x, svg_y = PositionGeometry.view_center( location_view )
        return self._shape_at_point(
            entity = entity,
            location_view = location_view,
            svg_x = svg_x,
            svg_y = svg_y,
        )

    def shapes_for_entities( self,
                             entities       : List[Entity],
                             location_view  : LocationView ) -> List[PlacementShape]:
        """Return one shape per entity in input order. Single-entity
        input degenerates to ``shape_for_entity``. Larger groups get
        a centered grid; each entity's slot becomes either a Point
        (icon entities) or a Path centered on that slot (path
        entities)."""
        total = len( entities )
        if total == 0:
            return []
        if total == 1:
            return [ self.shape_for_entity(
                entity = entities[0], location_view = location_view ) ]

        return [
            self._shape_at_grid_slot(
                entity = entity,
                location_view = location_view,
                grid_index = index,
                grid_total = total,
            )
            for index, entity in enumerate( entities )
        ]

    def default_icon_scale( self,
                            entity         : Entity,
                            location_view  : LocationView ) -> Decimal:
        """Default scale for an icon entity. Delegates to
        ``PositionGeometry.default_icon_scale``."""
        return PositionGeometry.default_icon_scale(
            entity = entity, location_view = location_view )

    # ----- internal shape routing (no DB) -----

    def _shape_at_grid_slot( self,
                             entity         : Entity,
                             location_view  : LocationView,
                             grid_index     : int,
                             grid_total     : int ) -> PlacementShape:
        svg_x, svg_y = PositionGeometry.grid_slot(
            location_view = location_view,
            grid_index = grid_index,
            grid_total = grid_total,
        )
        return self._shape_at_point(
            entity = entity,
            location_view = location_view,
            svg_x = svg_x,
            svg_y = svg_y,
        )

    def _shape_at_point( self,
                         entity         : Entity,
                         location_view  : LocationView,
                         svg_x          : float,
                         svg_y          : float ) -> PlacementShape:
        entity_type = entity.entity_type
        if entity_type.requires_path():
            svg_path = PathGeometry.create_default_path_string(
                location_view = location_view,
                is_path_closed = entity_type.requires_closed_path(),
                center_x = svg_x,
                center_y = svg_y,
                entity_type = entity_type,
            )
            return PlacementPath( svg_path = svg_path )

        return PlacementPoint(
            svg_x = svg_x,
            svg_y = svg_y,
            svg_scale = self.default_icon_scale(
                entity = entity, location_view = location_view ),
        )


class EntityPlacer:
    """DB-touching placement operations. Persists shapes computed by
    EntityPlacementCalculator and links entities into LocationViews.
    Pulls in delegate entities so callers don't have to. Also owns
    user-drawn-path persistence, edit-form construction, and
    entity-type transitions (icon ↔ path)."""

    def __init__( self ):
        self._calculator = EntityPlacementCalculator()
        return

    @property
    def calculator(self) -> EntityPlacementCalculator:
        return self._calculator

    def place_entity_in_view( self,
                              entity           : Entity,
                              location_view    : LocationView,
                              placement_shape  : Optional[PlacementShape] = None,
                              bulk_grid_index  : Optional[int]            = None,
                              bulk_grid_total  : Optional[int]            = None ):
        """Place a single entity into a location view, including its
        delegate entities. Idempotent: existing position/path/view rows
        are preserved.

        Three input modes for shape selection (in priority order):

        1. Caller provides ``placement_shape`` directly — used.
        2. Caller provides ``bulk_grid_index`` + ``bulk_grid_total``
           (legacy form-driven flow) — calculator picks the slot.
        3. Otherwise — calculator centers the shape on the viewbox.

        Delegates always go through mode (3): each delegate is placed
        at the viewbox center. See module docstring on the
        delegate-overlap limitation.
        """
        with transaction.atomic():
            if not entity.entity_views.all().exists():
                delegate_entity_list = (
                    EntityPairingManager().get_delegate_entities_with_defaults(
                        entity = entity )
                )
            else:
                delegate_entity_list = (
                    EntityPairingManager().get_delegate_entities( entity = entity )
                )

            if placement_shape is None:
                placement_shape = self._derive_placement_shape(
                    entity = entity,
                    location_view = location_view,
                    bulk_grid_index = bulk_grid_index,
                    bulk_grid_total = bulk_grid_total,
                )
            self._create_entity_view(
                entity = entity,
                location_view = location_view,
                placement_shape = placement_shape,
            )
            for delegate_entity in delegate_entity_list:
                delegate_shape = self._calculator.shape_for_entity(
                    entity = delegate_entity,
                    location_view = location_view,
                )
                self._create_entity_view(
                    entity = delegate_entity,
                    location_view = location_view,
                    placement_shape = delegate_shape,
                )
                continue
        return

    def place_entities_in_view( self,
                                entities       : List[Entity],
                                location_view  : LocationView ):
        """Place a group of entities into a location view in a single
        layout pass. Used by the post-sync dispatcher to position all
        items in a result group together. The grid is computed once
        across the entire group; per-entity delegates are placed by
        the single-entity flow."""
        shapes = self._calculator.shapes_for_entities(
            entities = entities,
            location_view = location_view,
        )
        with transaction.atomic():
            for entity, shape in zip( entities, shapes ):
                self.place_entity_in_view(
                    entity = entity,
                    location_view = location_view,
                    placement_shape = shape,
                )
                continue
        return

    def toggle_entity_in_view( self,
                               entity         : Entity,
                               location_view  : LocationView ) -> bool:
        """Add the entity to the view if absent, or remove it if
        present. Returns True if the entity is now in the view, False
        otherwise."""
        try:
            self.unplace_entity_from_view(
                entity = entity, location_view = location_view )
            return False
        except EntityView.DoesNotExist:
            self.place_entity_in_view(
                entity = entity, location_view = location_view )
            return True

    def ensure_default_shape_persisted( self,
                                        entity         : Entity,
                                        location_view  : LocationView ):
        """Ensure the entity has either an EntityPosition or
        EntityPath row for the location, creating it with default
        placement if missing. Does NOT create an EntityView link.

        Used by entity-type transition flows that already have an
        EntityView and just need a shape row to exist (e.g., a type
        change to a path-based type when no path row exists yet)."""
        shape = self._calculator.shape_for_entity(
            entity = entity,
            location_view = location_view,
        )
        self._persist_placement_shape(
            entity = entity,
            location_view = location_view,
            placement_shape = shape,
        )
        return

    def unplace_entity_from_view( self,
                                  entity         : Entity,
                                  location_view  : LocationView ):
        """Remove an entity (and its no-longer-needed delegates) from a
        location view. Raises ``EntityView.DoesNotExist`` if the entity
        is not in the view."""
        with transaction.atomic():
            self._delete_entity_view(
                entity = entity,
                location_view = location_view,
            )
            EntityPairingManager().remove_delegate_entities_from_view_if_needed(
                entity = entity,
                location_view = location_view,
            )
        return

    def set_entity_path( self,
                         entity_id     : int,
                         location      : Location,
                         svg_path_str  : str        ) -> EntityPath:
        """Persist a user-drawn path string into an ``EntityPath``
        row, creating one if absent or updating in place if
        present."""
        with transaction.atomic():
            try:
                entity_path = EntityPath.objects.get(
                    location = location,
                    entity_id = entity_id,
                )
                entity_path.svg_path = svg_path_str
                entity_path.save()
                return entity_path

            except EntityPath.DoesNotExist:
                pass

            entity = Entity.objects.get( id = entity_id )
            return EntityPath.objects.create(
                entity = entity,
                location = location,
                svg_path = svg_path_str,
            )

    def get_entity_position_form( self,
                                  entity         : Entity,
                                  location_view  : LocationView ) -> Optional[EntityPositionForm]:
        """Return an ``EntityPositionForm`` bound to the entity's
        existing position in this location, or None if the entity has
        no position row. Used by the entity edit-mode UI."""
        if not location_view:
            return None
        entity_position = EntityPosition.objects.filter(
            entity = entity,
            location = location_view.location,
        ).first()
        if not entity_position:
            return None
        return EntityPositionForm(
            location_view.location.svg_position_bounds,
            instance = entity_position,
        )

    def handle_entity_type_transition(
            self,
            entity         : Entity,
            location_view  : LocationView   = None ) -> Tuple[bool, EntityTransitionType]:
        """Transition an entity's persisted geometry between icon
        (EntityPosition) and path (EntityPath) representations
        following an entity_type change.

        Preservation strategy: when both representations already
        exist, leave both rows in place and just classify the
        transition for the caller. When only one exists and the new
        type needs the other, build the missing one from the
        existing one's center (path → icon uses path geometric
        center; icon → path uses position center) so the visual
        location is preserved across the type change. When neither
        exists, create a default-placement shape.

        Returns (transition_occurred, transition_type)."""
        if not location_view:
            return False, EntityTransitionType.NO_LOCATION_VIEW

        entity_type = entity.entity_type

        entity_position = EntityPosition.objects.filter(
            entity = entity,
            location = location_view.location,
        ).first()
        entity_path = EntityPath.objects.filter(
            entity = entity,
            location = location_view.location,
        ).first()

        has_position = bool( entity_position )
        has_path = bool( entity_path )
        needs_position = entity_type.requires_position()
        needs_path = entity_type.requires_path()

        had_both = has_position and has_path

        if had_both:
            with transaction.atomic():
                if needs_position:
                    return self._transition_path_to_icon(
                        entity = entity,
                        location_view = location_view,
                        entity_path = entity_path,
                    )
                else:
                    return self._transition_icon_to_path(
                        entity = entity,
                        location_view = location_view,
                        entity_position = entity_position,
                        is_path_closed = entity_type.requires_closed_path(),
                    )

        with transaction.atomic():
            if needs_position:
                if not has_position:
                    if has_path:
                        return self._transition_path_to_icon(
                            entity = entity,
                            location_view = location_view,
                            entity_path = entity_path,
                        )
                    self.ensure_default_shape_persisted(
                        entity = entity,
                        location_view = location_view,
                    )
                    return True, EntityTransitionType.CREATED_POSITION
                return True, EntityTransitionType.ICON_TO_ICON

            elif needs_path:
                if not has_path:
                    if has_position:
                        return self._transition_icon_to_path(
                            entity = entity,
                            location_view = location_view,
                            entity_position = entity_position,
                            is_path_closed = entity_type.requires_closed_path(),
                        )
                    self.ensure_default_shape_persisted(
                        entity = entity,
                        location_view = location_view,
                    )
                    return True, EntityTransitionType.CREATED_PATH
                return True, EntityTransitionType.PATH_TO_PATH

        return False, EntityTransitionType.NO_TRANSITION_NEEDED

    # ----- internal helpers -----

    def _derive_placement_shape( self,
                                 entity           : Entity,
                                 location_view    : LocationView,
                                 bulk_grid_index  : Optional[int],
                                 bulk_grid_total  : Optional[int] ) -> PlacementShape:
        if (
            bulk_grid_total is not None
            and bulk_grid_total > 1
            and bulk_grid_index is not None
        ):
            return self._calculator._shape_at_grid_slot(
                entity = entity,
                location_view = location_view,
                grid_index = bulk_grid_index,
                grid_total = bulk_grid_total,
            )
        return self._calculator.shape_for_entity(
            entity = entity, location_view = location_view )

    def _create_entity_view( self,
                             entity           : Entity,
                             location_view    : LocationView,
                             placement_shape  : PlacementShape ) -> EntityView:
        with transaction.atomic():
            self._persist_placement_shape(
                entity = entity,
                location_view = location_view,
                placement_shape = placement_shape,
            )
            try:
                entity_view = EntityView.objects.get(
                    entity = entity,
                    location_view = location_view,
                )
            except EntityView.DoesNotExist:
                entity_view = EntityView.objects.create(
                    entity = entity,
                    location_view = location_view,
                )
        return entity_view

    def _delete_entity_view( self,
                             entity         : Entity,
                             location_view  : LocationView ):
        entity_view = EntityView.objects.get(
            entity = entity,
            location_view = location_view,
        )
        entity_view.delete()
        return

    def _persist_placement_shape( self,
                                  entity           : Entity,
                                  location_view    : LocationView,
                                  placement_shape  : PlacementShape ):
        if isinstance( placement_shape, PlacementPoint ):
            self._persist_position_if_needed(
                entity = entity,
                location_view = location_view,
                placement_point = placement_shape,
            )
        elif isinstance( placement_shape, PlacementPath ):
            self._persist_path_if_needed(
                entity = entity,
                location_view = location_view,
                placement_path = placement_shape,
            )
        else:
            raise TypeError(
                f'Unrecognized placement shape: {type(placement_shape).__name__}'
            )
        return

    def _persist_position_if_needed(
            self,
            entity           : Entity,
            location_view    : LocationView,
            placement_point  : PlacementPoint ) -> Optional[EntityPosition]:
        try:
            return EntityPosition.objects.get(
                location = location_view.location,
                entity = entity,
            )
        except EntityPosition.DoesNotExist:
            pass

        return EntityPosition.objects.create(
            entity = entity,
            location = location_view.location,
            svg_x = Decimal( str( placement_point.svg_x ) ),
            svg_y = Decimal( str( placement_point.svg_y ) ),
            svg_scale = placement_point.svg_scale,
            svg_rotate = Decimal( '0.0' ),
        )

    def _persist_path_if_needed(
            self,
            entity          : Entity,
            location_view   : LocationView,
            placement_path  : PlacementPath ) -> Optional[EntityPath]:
        try:
            return EntityPath.objects.get(
                location = location_view.location,
                entity = entity,
            )
        except EntityPath.DoesNotExist:
            pass

        return EntityPath.objects.create(
            entity = entity,
            location = location_view.location,
            svg_path = placement_path.svg_path,
        )

    def _transition_icon_to_path(
            self,
            entity           : Entity,
            location_view    : LocationView,
            entity_position  : EntityPosition,
            is_path_closed   : bool ) -> Tuple[bool, EntityTransitionType]:
        """Create an EntityPath centered on the existing position so
        the visual location is preserved. Existing EntityPath rows
        (if any) are preserved verbatim (preservation strategy
        allows easy reversion)."""
        center_x = float( entity_position.svg_x )
        center_y = float( entity_position.svg_y )

        svg_path = PathGeometry.create_default_path_string(
            location_view = location_view,
            is_path_closed = is_path_closed,
            center_x = center_x,
            center_y = center_y,
            entity_type = entity.entity_type,
            radius_multiplier = 2.0,  # Larger for control-point visibility.
        )
        EntityPath.objects.get_or_create(
            entity = entity,
            location = location_view.location,
            defaults = { 'svg_path': svg_path },
        )
        return True, EntityTransitionType.ICON_TO_PATH

    def _transition_path_to_icon(
            self,
            entity         : Entity,
            location_view  : LocationView,
            entity_path    : EntityPath ) -> Tuple[bool, EntityTransitionType]:
        """Create an EntityPosition at the existing path's geometric
        center so the visual location is preserved. Falls back to
        the viewbox center when path-center extraction fails.
        Existing EntityPosition rows (if any) are preserved
        verbatim."""
        center_x, center_y = PositionGeometry.path_center( entity_path.svg_path )
        if center_x is None or center_y is None:
            center_x, center_y = PositionGeometry.view_center( location_view )

        svg_scale = self._calculator.default_icon_scale(
            entity = entity, location_view = location_view )
        EntityPosition.objects.get_or_create(
            entity = entity,
            location = location_view.location,
            defaults = {
                'svg_x': Decimal( str( center_x ) ),
                'svg_y': Decimal( str( center_y ) ),
                'svg_scale': svg_scale,
                'svg_rotate': Decimal( '0.0' ),
            },
        )
        return True, EntityTransitionType.PATH_TO_ICON
