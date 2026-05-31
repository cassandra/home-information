"""
Per-integration EXTERNAL_REFERENCE base class.

Each integration that advertises
``IntegrationCapability.EXTERNAL_REFERENCE`` provides a concrete
subclass and returns an instance from
``IntegrationGateway.get_external_referencer()``. The framework
owns the picker UI, attach dispatcher, and the
EntityExternalReference / LocationExternalReference tables; the
integration participates by (a) translating a search query into
``ExternalReferenceResult`` candidates and (b) attaching selected
candidates as rows on those tables, fetching thumbnail bytes from
upstream as part of attach.
"""

import logging
from typing import List, Optional

from hi.integrations.capability_gateway import CapabilityGateway
from hi.integrations.enums import IntegrationCapability
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationValidationResult

from .transient_models import (
    ExternalReferenceAttachBatchOutcome,
    ExternalReferenceAttachOutcome,
    ExternalReferenceResult,
    ExternalReferenceSearchResult,
)


class IntegrationExternalReferencer( CapabilityGateway ):

    """Search-and-attach surface contributed by integrations that
    expose a queryable corpus of linkable resources (documents,
    pages, files in an external CMS, etc.). The framework calls
    ``search_references`` from the picker view and presents the
    returned candidates to the operator for multi-select attach."""

    capability = IntegrationCapability.EXTERNAL_REFERENCE

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute],
    ) -> IntegrationValidationResult:
        """Schema-only validation of the proposed configuration.
        Must NOT perform network operations."""
        raise NotImplementedError('Subclasses must override this method')

    def search_references(
            self,
            query: str,
            limit: int = 20,
    ) -> ExternalReferenceSearchResult:
        """Query the upstream corpus and return up to ``limit``
        candidates wrapped in an
        ``ExternalReferenceSearchResult``. Operators see the
        returned list rendered as cards (thumbnail/mime-icon +
        title + snippet + clickable source URL); multi-selecting
        any subset attaches them via ``attach_references`` on the
        host Entity or Location.

        Implementations should:
          - Return ``ExternalReferenceSearchResult(results=[])``
            when the query yields no matches (no ``error_message``).
          - Populate ``error_message`` when the upstream call fails
            (auth rejected, unreachable, etc.) so the picker
            surfaces a banner instead of "No results.". The picker
            stays usable across failures; do not raise.
          - Honor ``limit`` as an upper bound (the picker uses a
            user-selectable page-size 20/50/100).
          - Order results by upstream relevance (most-relevant
            first); the picker preserves this order.
          - Not raise on empty/whitespace queries; return
            ``ExternalReferenceSearchResult(results=[])``.
        """
        raise NotImplementedError('Subclasses must override this method')

    def attach_references(
            self,
            owner,
            selections: List[ExternalReferenceResult],
    ) -> ExternalReferenceAttachBatchOutcome:
        """Attach the operator-selected upstream items as
        ExternalReference rows on the given owner (Entity or
        Location). Concrete here: subclasses contribute the upstream
        client and per-selection attach logic via ``_build_client``,
        ``_try_upstream_thumbnail``, and ``_try_generate_from_original``.

        Returns one ``ExternalReferenceAttachOutcome`` per selection
        wrapped in an ``ExternalReferenceAttachBatchOutcome``. The
        framework dispatcher hands the composite to the view; the
        view chooses the next modal (owner edit on full success,
        error modal otherwise) from the aggregate counts.

        Failure semantics:
          - A failure to build the upstream client synthesizes an
            all-failure batch (one outcome per selection), so the
            error modal carries an outcome count consistent with
            what the operator selected.
          - Per-selection exceptions become ``success=False``
            outcomes with an operator-readable ``error_message``;
            they do NOT abort the rest of the batch. Batch-level
            atomicity is deliberately NOT used -- it would defeat
            the per-selection isolation. Per-row consistency is
            owned by ``create_or_update``.
          - A missing thumbnail is NOT a failure outcome -- the
            placeholder render covers it.
        """
        label = self.get_metadata().label
        try:
            client = self.build_client()
        except IntegrationAttributeError as e:
            self.logger.warning( f'{label} attach aborted: {e}' )
            return self._all_failure_batch(
                selections,
                f'{label} integration is not configured.',
            )
        except Exception as e:
            self.logger.exception( f'{label} client build failed: {e}' )
            return self._all_failure_batch(
                selections,
                f'{label} integration error -- see server logs.',
            )

        outcomes : List[ExternalReferenceAttachOutcome] = []
        manager = self._manager_for_owner( owner )
        for selection in selections:
            try:
                self._attach_one( client, manager, owner, selection )
                outcomes.append( ExternalReferenceAttachOutcome(
                    success = True,
                ) )
            except Exception as e:
                self.logger.warning(
                    f'{label} attach failed for '
                    f'{selection.integration_key.integration_name}: {e}'
                )
                outcomes.append( ExternalReferenceAttachOutcome(
                    success = False,
                    error_message = (
                        f'{label} could not attach '
                        f'{selection.title!r} -- see server logs.'
                    ),
                ) )
        return ExternalReferenceAttachBatchOutcome( outcomes = outcomes )

    def _attach_one(
            self, client, manager, owner,
            selection : ExternalReferenceResult,
    ) -> None:
        """Per-selection attach: fetch a thumbnail via the defensive
        chain (upstream -> HI-generated from original -> none) then
        upsert via the framework manager. Subclasses supply the
        two thumbnail-fetch hooks; both may return None and the row
        is created either way."""
        integration_name = selection.integration_key.integration_name
        mime_type = selection.mime_type or ''
        thumbnail_bytes = self._try_upstream_thumbnail(
            client, integration_name,
        )
        if thumbnail_bytes is None:
            thumbnail_bytes = self._try_generate_from_original(
                client, integration_name, mime_type,
            )
        manager.create_or_update(
            owner           = owner,
            integration_key = selection.integration_key,
            title           = selection.title,
            source_url      = selection.source_url,
            mime_type       = mime_type,
            thumbnail_bytes = thumbnail_bytes,
        )

    def build_client(self):
        """Build and return the integration's upstream client. The
        usual subclass binding is ``build_client =
        staticmethod(module_build_client)`` -- the module-level
        client factory IS the interface implementation, no wrapper
        method needed.

        May raise ``IntegrationAttributeError`` for configuration
        problems (becomes an "integration is not configured"
        all-failure batch); any other exception becomes a generic
        "integration error -- see server logs" all-failure batch."""
        raise NotImplementedError('Subclasses must override this method')

    def _try_upstream_thumbnail(
            self, client, integration_name : str,
    ) -> Optional[bytes]:
        """Return upstream thumbnail bytes for ``integration_name``,
        or None when none can be fetched. Must not raise."""
        raise NotImplementedError('Subclasses must override this method')

    def _try_generate_from_original(
            self, client, integration_name : str, mime_type : str,
    ) -> Optional[bytes]:
        """Return HI-generator thumbnail bytes from upstream
        original-bytes, or None when the integration can't / won't
        produce one for this mime type. Must not raise."""
        raise NotImplementedError('Subclasses must override this method')

    @staticmethod
    def _all_failure_batch(
            selections : List[ExternalReferenceResult],
            error_message : str,
    ) -> ExternalReferenceAttachBatchOutcome:
        return ExternalReferenceAttachBatchOutcome(
            outcomes = [
                ExternalReferenceAttachOutcome(
                    success = False, error_message = error_message,
                )
                for _ in selections
            ],
        )

    @property
    def logger(self) -> logging.Logger:
        # Resolve at call time so log lines surface under the
        # subclass's module (e.g. ``hi.services.paperless...``), not
        # this base module. Operators grepping by integration get
        # the per-module hits they expect.
        return logging.getLogger( self.__class__.__module__ )

    @staticmethod
    def _manager_for_owner(owner):
        """Resolve the framework external-reference manager for the
        given owner type. Imported lazily to avoid pulling the
        Entity / Location models into framework module-load order
        prematurely."""
        from hi.apps.entity.models import Entity
        from hi.integrations.models import (
            EntityExternalReference,
            LocationExternalReference,
        )
        if isinstance(owner, Entity):
            return EntityExternalReference.objects
        return LocationExternalReference.objects

    def get_attribute_actions_template_name(self) -> Optional[str]:
        """Per-capability template fragment to render in the
        integration attribute form's action bar. EXTERNAL_REFERENCE
        contributes the enabled/disabled status badge plus the
        Disable button. Individual integrations can override to
        substitute their own fragment."""
        return 'integrations/referencer/panes/attribute_actions.html'
