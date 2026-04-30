"""
Dispatcher modal form parser.

The dispatcher modal carries a three-level inheritance: top default
→ group default → per-entity. Empty selections at any level inherit
from the parent; explicit ``__skip__`` overrides inheritance with
"don't place this entity"; a top-level ``__new__`` value creates one
fresh ``LocationView`` named after the integration and uses it as
the resolved top default. Group/entity overrides to existing views
remain in effect even when the top is ``__new__``.

This module owns that translation logic. The view layer hands a
request + integration_data to ``DispatcherFormParser.parse(...)``
and gets back a list of ``PlacementDecision`` values; the parser
doesn't know HTTP, and the view doesn't know form-key conventions
or sentinel strings.
"""
import logging
from typing import List, Optional

from django.core.exceptions import BadRequest

from hi.apps.entity.entity_placement import PlacementDecision
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView

logger = logging.getLogger(__name__)


class DispatcherFormParser:
    """Translates dispatcher modal form input into a list of
    ``PlacementDecision`` values, applying three-level inheritance
    and the skip / new-view sentinels.

    Form-input contract (matches dispatcher.html):

    * ``top_view`` — top-level default for every imported entity.
      Values: '' (skip all), '__new__' (create a fresh view),
      or '<view_id>' (existing view).
    * For each group i:
        - ``all_group_{i}_entity_ids`` lists every entity id.
        - ``group_view_{i}`` is the group choice. Values: ''
          (use top), '__skip__' (explicit skip), '<view_id>'.
        - ``group_{i}_entity_{E}_view`` is the per-entity
          override. Values: '' (use group), '__skip__', '<view_id>'.
    * For ungrouped:
        - ``ungrouped_entity_ids`` lists every entity.
        - ``ungrouped_entity_{E}_view`` is the per-entity choice
          against the top default. Values: '' (use top),
          '__skip__', '<view_id>'.
    """

    # An empty string in any of the three slots means "inherit from
    # parent level"; FORM_VALUE_SKIP is an explicit no-op overriding
    # inheritance; FORM_VALUE_NEW_VIEW is offered only at the top
    # level and triggers fresh-LocationView creation.
    FORM_VALUE_SKIP = '__skip__'
    FORM_VALUE_NEW_VIEW = '__new__'

    @classmethod
    def parse( cls, request, integration_data ) -> List[PlacementDecision]:
        decisions = []
        view_lookup = cls._build_view_lookup()

        top_value = request.POST.get('top_view', '').strip()
        top_view = cls._resolve_top_view(
            request = request,
            top_value = top_value,
            view_lookup = view_lookup,
            integration_data = integration_data,
        )

        # Discover group indices by scanning POST keys.
        group_indices = sorted({
            int(k.split('_')[2])
            for k in request.POST.keys()
            if k.startswith('all_group_') and k.endswith('_entity_ids')
        })
        for group_index in group_indices:
            group_value = request.POST.get(
                f'group_view_{group_index}', '' ).strip()
            group_choice = cls._resolve_child_choice(
                form_value = group_value,
                parent_view = top_view,
                view_lookup = view_lookup,
            )
            entity_id_list = request.POST.getlist(
                f'all_group_{group_index}_entity_ids' )
            entities = list( Entity.objects.filter(
                id__in = [int(e) for e in entity_id_list]
            ) )
            entity_by_id = { e.id: e for e in entities }
            for entity_id_str in entity_id_list:
                entity = entity_by_id.get( int(entity_id_str) )
                if entity is None:
                    continue
                entity_value = request.POST.get(
                    f'group_{group_index}_entity_{entity.id}_view', '' ).strip()
                entity_choice = cls._resolve_child_choice(
                    form_value = entity_value,
                    parent_view = group_choice,
                    view_lookup = view_lookup,
                )
                decisions.append( PlacementDecision(
                    entity = entity, location_view = entity_choice,
                ) )

        # Ungrouped items: no group level — entity inherits from top.
        ungrouped_ids = request.POST.getlist( 'ungrouped_entity_ids' )
        if ungrouped_ids:
            ungrouped = list( Entity.objects.filter(
                id__in = [int(e) for e in ungrouped_ids]
            ) )
            ungrouped_by_id = { e.id: e for e in ungrouped }
            for entity_id_str in ungrouped_ids:
                entity = ungrouped_by_id.get( int(entity_id_str) )
                if entity is None:
                    continue
                entity_value = request.POST.get(
                    f'ungrouped_entity_{entity.id}_view', '' ).strip()
                entity_choice = cls._resolve_child_choice(
                    form_value = entity_value,
                    parent_view = top_view,
                    view_lookup = view_lookup,
                )
                decisions.append( PlacementDecision(
                    entity = entity, location_view = entity_choice,
                ) )

        return decisions

    @classmethod
    def _resolve_top_view( cls,
                           request,
                           top_value        : str,
                           view_lookup      : dict,
                           integration_data ) -> Optional[LocationView]:
        """Top-level form value → resolved LocationView (or None for skip).

        Three valid top values: ''=skip-all, '__new__'=create fresh
        view, '<id>'=existing view. Creation of the new view is the
        side effect of '__new__'; the new view becomes the top
        default for everything else.
        """
        if top_value == cls.FORM_VALUE_NEW_VIEW:
            return cls._create_new_view(
                request = request, integration_data = integration_data )
        if top_value == '':
            return None
        return view_lookup.get( top_value )

    @classmethod
    def _resolve_child_choice( cls,
                               form_value   : str,
                               parent_view  : Optional[LocationView],
                               view_lookup  : dict ) -> Optional[LocationView]:
        """Group/entity form value → resolved LocationView (or None
        for skip). Empty inherits from parent; '__skip__' is an
        explicit no-op that overrides any inherited parent value;
        otherwise it's an explicit existing-view id."""
        if form_value == '':
            return parent_view
        if form_value == cls.FORM_VALUE_SKIP:
            return None
        return view_lookup.get( form_value )

    @classmethod
    def _create_new_view( cls, request, integration_data ) -> LocationView:
        """Create a single LocationView named after the integration
        label, attached to the operator's current default Location
        (per session view_parameters). LocationManager's
        get_default_location handles the session-first lookup with
        a DB-order fallback when nothing is set."""
        try:
            location = LocationManager().get_default_location( request = request )
        except Location.DoesNotExist:
            raise BadRequest(
                'Cannot create a new view: no Location is configured.'
            )
        return LocationManager().create_location_view(
            location = location,
            name = integration_data.label,
        )

    @classmethod
    def _build_view_lookup( cls ) -> dict:
        return { str(v.id): v for v in LocationView.objects.all() }
