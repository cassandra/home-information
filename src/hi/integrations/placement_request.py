"""
Placement view request shape — parsing the inputs, encoding the
outputs.

The placement modal carries two related concerns that this module
owns:

* ``PlacementUrlParams`` — the URL/form-param contract
  (``is_initial_import``, ``entity_ids``). Single source of truth
  for key names and value encodings; build URLs and parse requests
  via this class rather than handling raw strings.

* ``PlacementFormParser`` — the placement-form-body parser. The
  placement modal carries a three-level inheritance: top default
  → group default → per-entity. Empty selections at any level
  inherit from the parent; explicit ``__skip__`` overrides
  inheritance with "don't place this entity"; a top-level
  ``__new_view__`` value creates one fresh ``LocationView`` named
  after the integration; a top-level ``__new_collection__`` value
  creates one fresh ``Collection``. Group/entity overrides to
  existing views or collections remain in effect even when the
  top is one of the new-* sentinels.

  Form values for the dropdowns are *tagged* so views and
  collections can share the same select element without colliding
  on numeric ids:

    ``view:<id>``        — existing LocationView
    ``collection:<id>``  — existing Collection
    ``__new_view__``     — create one fresh LocationView (top only)
    ``__new_collection__`` — create one fresh Collection (top only)
    ``__skip__``         — explicit no-op overriding parent
    ``''``               — inherit from parent (top → skip-all)

  ``parse(request, integration_data)`` returns a list of
  ``PlacementDecision`` values for the placement service to apply.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from django.core.exceptions import BadRequest
from django.utils.http import urlencode

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection
from hi.apps.common.utils import str_to_bool
from hi.apps.entity.entity_placement import PlacementDecision
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlacementUrlParams:
    """Encoded contract for the placement view's URL/form params.

    Single source of truth for key names, value encodings, and
    list separators — callers build URLs and parse requests via
    this class rather than handling raw strings. Renaming a key
    or changing an encoding happens in exactly one place.

    Scope: the URL query params (``?is_initial_import=…&entity_ids=…``)
    and the matching hidden form fields the placement modal POSTs
    back. Does *not* cover the per-entity / per-group form fields
    consumed by ``PlacementFormParser`` — those have their own
    contract owned by that parser.
    """

    KEY_IS_INITIAL_IMPORT = 'is_initial_import'
    KEY_ENTITY_IDS = 'entity_ids'
    ENTITY_IDS_SEP = ','
    TRUE_VALUE = '1'
    FALSE_VALUE = '0'

    is_initial_import : bool        = False
    entity_ids        : List[int]   = field(default_factory=list)

    def to_query_dict(self) -> Dict[str, str]:
        """Sparse query dict — keys are omitted when their value
        is the default, keeping URLs free of redundant
        ``?is_initial_import=0`` cruft."""
        result : Dict[str, str] = {}
        if self.is_initial_import:
            result[self.KEY_IS_INITIAL_IMPORT] = self.TRUE_VALUE
        if self.entity_ids:
            result[self.KEY_ENTITY_IDS] = self.ENTITY_IDS_SEP.join(
                str(i) for i in self.entity_ids
            )
        return result

    def append_to_url( self, base_url : str ) -> str:
        """Return ``base_url`` with these params encoded as a
        query string. Empty params produce no '?' suffix."""
        qd = self.to_query_dict()
        return f'{base_url}?{urlencode(qd)}' if qd else base_url

    def is_initial_import_form_value(self) -> str:
        """The hidden-form-field encoding of ``is_initial_import``
        for templates that need to round-trip the flag through a
        POST."""
        return self.TRUE_VALUE if self.is_initial_import else self.FALSE_VALUE

    @classmethod
    def from_data(cls, data) -> 'PlacementUrlParams':
        """Parse from ``request.GET`` or ``request.POST`` (or any
        QueryDict-like). Malformed ``entity_ids`` raises BadRequest
        so a tampered request fails loudly rather than silently
        widening scope."""
        is_initial = str_to_bool( data.get( cls.KEY_IS_INITIAL_IMPORT, '' ) )
        raw = ( data.get( cls.KEY_ENTITY_IDS, '' ) or '' ).strip()
        entity_ids : List[int] = []
        if raw:
            try:
                entity_ids = [
                    int( piece )
                    for piece in raw.split( cls.ENTITY_IDS_SEP )
                    if piece.strip()
                ]
            except ValueError:
                raise BadRequest( f'Invalid {cls.KEY_ENTITY_IDS} parameter.' )
        return cls( is_initial_import = is_initial, entity_ids = entity_ids )


class PlacementFormParser:
    """Translates placement modal form input into a list of
    ``PlacementDecision`` values, applying three-level inheritance
    and the skip / new-view / new-collection sentinels."""

    FORM_VALUE_SKIP = '__skip__'
    FORM_VALUE_NEW_VIEW = '__new_view__'
    FORM_VALUE_NEW_COLLECTION = '__new_collection__'

    @classmethod
    def parse( cls, request, integration_data ) -> List[PlacementDecision]:
        decisions = []
        view_lookup = cls._build_view_lookup()
        collection_lookup = cls._build_collection_lookup()

        top_value = request.POST.get('top_view', '').strip()
        top_target = cls._resolve_top_target(
            request = request,
            top_value = top_value,
            view_lookup = view_lookup,
            collection_lookup = collection_lookup,
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
            group_target = cls._resolve_child_choice(
                form_value = group_value,
                parent_target = top_target,
                view_lookup = view_lookup,
                collection_lookup = collection_lookup,
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
                entity_target = cls._resolve_child_choice(
                    form_value = entity_value,
                    parent_target = group_target,
                    view_lookup = view_lookup,
                    collection_lookup = collection_lookup,
                )
                decisions.append( cls._make_decision(
                    entity = entity, target = entity_target,
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
                entity_target = cls._resolve_child_choice(
                    form_value = entity_value,
                    parent_target = top_target,
                    view_lookup = view_lookup,
                    collection_lookup = collection_lookup,
                )
                decisions.append( cls._make_decision(
                    entity = entity, target = entity_target,
                ) )

        return decisions

    @classmethod
    def _make_decision( cls, entity, target ) -> PlacementDecision:
        """target is a 2-tuple (location_view, collection) where at
        most one is non-None, or (None, None) for skip."""
        location_view, collection = target
        return PlacementDecision(
            entity = entity,
            location_view = location_view,
            collection = collection,
        )

    @classmethod
    def _resolve_top_target( cls,
                             request,
                             top_value         : str,
                             view_lookup       : dict,
                             collection_lookup : dict,
                             integration_data,
                             ) -> Tuple[Optional[LocationView], Optional[Collection]]:
        """Top-level form value → (location_view, collection) target.

        Top values: ''=skip-all, '__new_view__'=create fresh view,
        '__new_collection__'=create fresh collection,
        'view:<id>'=existing view, 'collection:<id>'=existing
        collection. Creating a new view/collection is the side
        effect of the corresponding sentinel; the new object
        becomes the top default for everything else.
        """
        if top_value == cls.FORM_VALUE_NEW_VIEW:
            return cls._create_new_view(
                request = request, integration_data = integration_data,
            ), None
        if top_value == cls.FORM_VALUE_NEW_COLLECTION:
            return None, cls._create_new_collection(
                integration_data = integration_data,
            )
        if top_value == '':
            return None, None
        return cls._lookup_tagged_target(
            tagged_value = top_value,
            view_lookup = view_lookup,
            collection_lookup = collection_lookup,
        )

    @classmethod
    def _resolve_child_choice(
            cls,
            form_value         : str,
            parent_target      : Tuple[Optional[LocationView], Optional[Collection]],
            view_lookup        : dict,
            collection_lookup  : dict,
    ) -> Tuple[Optional[LocationView], Optional[Collection]]:
        """Group/entity form value → (location_view, collection)
        target. Empty inherits from parent; '__skip__' overrides
        any inherited parent value with skip; otherwise it's a
        tagged existing-target id ('view:<id>' or 'collection:<id>').
        Group/entity dropdowns do not offer the new-* sentinels —
        only the top level can create a new target."""
        if form_value == '':
            return parent_target
        if form_value == cls.FORM_VALUE_SKIP:
            return None, None
        return cls._lookup_tagged_target(
            tagged_value = form_value,
            view_lookup = view_lookup,
            collection_lookup = collection_lookup,
        )

    @classmethod
    def _lookup_tagged_target(
            cls,
            tagged_value       : str,
            view_lookup        : dict,
            collection_lookup  : dict,
    ) -> Tuple[Optional[LocationView], Optional[Collection]]:
        """Parse 'view:<id>' or 'collection:<id>' into a
        (location_view, collection) tuple. Unknown tag prefix or
        missing id resolves to skip."""
        if ':' not in tagged_value:
            return None, None
        kind, _, raw_id = tagged_value.partition(':')
        if kind == 'view':
            return view_lookup.get( raw_id ), None
        if kind == 'collection':
            return None, collection_lookup.get( raw_id )
        return None, None

    @classmethod
    def _create_new_view( cls, request, integration_data ) -> LocationView:
        """Create a single LocationView named after the integration
        label, attached to the operator's current default Location.
        ``LocationManager.create_location_view`` handles name
        collisions via its built-in disambiguation."""
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
    def _create_new_collection( cls, integration_data ) -> Collection:
        """Create a single Collection named after the integration
        label. ``CollectionManager.create_collection`` handles name
        collisions via its built-in disambiguation."""
        return CollectionManager().create_collection(
            name = integration_data.label,
        )

    @classmethod
    def _build_view_lookup( cls ) -> dict:
        return { str(v.id): v for v in LocationView.objects.all() }

    @classmethod
    def _build_collection_lookup( cls ) -> dict:
        return { str(c.id): c for c in Collection.objects.all() }
