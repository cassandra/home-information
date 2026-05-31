"""View mixins for the EXTERNAL_REFERENCE capability.

Helpers specific to the capability live here so view files are all
view classes and no orphan module-level utilities. Shared across
the picker / search / attach views and available to any future
external-reference view.
"""

import logging
from typing import List, Tuple

from django.core.exceptions import BadRequest
from django.http import Http404

from hi.apps.entity.models import Entity
from hi.apps.location.models import Location
from hi.constants import DIVID
from hi.enums import ItemType

from hi.integrations.integration_data import IntegrationData

from .integration_referencer import IntegrationExternalReferencer
from .transient_models import ExternalReferenceSearchResult


logger = logging.getLogger(__name__)


class ExternalReferenceViewMixin:
    """Shared helpers for EXTERNAL_REFERENCE views: integration
    resolution from form-posted ids, raw-form owner resolution, and
    upstream search with a labeled fallback banner. The supported
    owner ItemTypes are the two external-references can attach to
    (entities and locations)."""

    PAGE_SIZE_CHOICES = (20, 50, 100)
    DEFAULT_LIMIT = 20

    OWNER_MODELS = {
        ItemType.ENTITY: Entity,
        ItemType.LOCATION: Location,
    }

    def resolve_integration_data(
            self,
            integration_data_list : List[IntegrationData],
            integration_id        : str,
    ) -> IntegrationData:
        """Map the form's posted integration_id to one of the
        currently-enabled referencer integrations. Rejects unknown
        or now-disabled ids so a stale modal can't drive an action
        against an integration the operator has turned off."""
        if not integration_id:
            raise BadRequest(
                f'Missing {DIVID["REF_PICKER_INTEGRATION_ID_FIELD"]}.',
            )
        for candidate in integration_data_list:
            if candidate.integration_id == integration_id:
                return candidate
        raise BadRequest(
            f'Unknown {DIVID["REF_PICKER_INTEGRATION_ID_FIELD"]}: '
            f'{integration_id!r}',
        )

    def resolve_owner_from_form(
            self,
            raw_item_type : str,
            raw_item_id   : str,
    ) -> Tuple[ItemType, object]:
        """Parse the picker form's item_type + item_id and fetch
        the owner row. Returns ``(item_type, owner)``; raises
        BadRequest for unparseable / out-of-domain inputs and
        Http404 when the row doesn't exist."""
        try:
            item_type = ItemType.from_name( raw_item_type )
        except ValueError:
            raise BadRequest(
                f'Unsupported {DIVID["REF_PICKER_ITEM_TYPE_FIELD"]}: '
                f'{raw_item_type!r}',
            )
        if item_type not in self.OWNER_MODELS:
            raise BadRequest(
                f'Unsupported {DIVID["REF_PICKER_ITEM_TYPE_FIELD"]}: '
                f'{raw_item_type!r}',
            )
        try:
            item_id = int( raw_item_id )
        except (TypeError, ValueError):
            raise BadRequest(
                f'Invalid {DIVID["REF_PICKER_ITEM_ID_FIELD"]}.',
            )
        owner_model = self.OWNER_MODELS[ item_type ]
        try:
            owner = owner_model.objects.get( id = item_id )
        except owner_model.DoesNotExist:
            raise Http404( f'{item_type.label} not found.' )
        return item_type, owner

    def search_upstream(
            self,
            referencer : IntegrationExternalReferencer,
            query      : str,
            limit      : int,
    ) -> ExternalReferenceSearchResult:
        if not query:
            return ExternalReferenceSearchResult( results = [] )
        try:
            return referencer.search_references( query = query, limit = limit )
        except Exception:
            # The contract asks referencers to populate
            # ``error_message`` instead of raising, so reaching this
            # branch means the referencer itself is broken. Surface
            # a labeled message so operators with multiple
            # referencers know which one to look at; the stack lands
            # in the server log.
            logger.exception( 'Attribute-reference search failed.' )
            label = self._safe_label( referencer )
            return ExternalReferenceSearchResult(
                results = [],
                error_message = f'{label} search failed — see server logs.',
            )

    def _safe_label(
            self, referencer : IntegrationExternalReferencer,
    ) -> str:
        # Defensive: a referencer broken enough to raise from search
        # may also raise from get_metadata. Fall back to a generic
        # label so the banner never compounds the failure.
        try:
            return referencer.get_metadata().label
        except Exception:
            return 'Integration'
