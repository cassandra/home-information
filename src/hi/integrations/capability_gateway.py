"""Common base for the per-capability gateway peers.

``IntegrationConnector``, ``IntegrationImporter``, and
``IntegrationAttributeReferencer`` are the three per-capability
gateway classes today: each is the framework-facing surface for a
specific ``IntegrationCapability``. They are conceptually peers but
historically shared no base, leaving cross-capability concerns with
no natural home.

``CapabilityGateway`` is the shared base. Things that apply to *any*
capability (capability identification, operator-facing description,
attribute-form action extensions, etc.) live here. Things that are
genuinely capability-specific (sync, import, search) stay on the
subclass.

Adding a new capability means subclassing here, declaring the
``capability`` class attribute, and overriding only the methods that
make sense for the new shape.
"""
from typing import Optional

from .enums import IntegrationCapability
from .transient_models import IntegrationMetaData


class CapabilityGateway:
    """Base for per-capability gateway peers."""

    # Subclasses declare which ``IntegrationCapability`` they
    # realize. The framework reads this when iterating an
    # integration's capability gateways uniformly.
    capability: IntegrationCapability

    def get_metadata(self) -> IntegrationMetaData:
        """Return the integration's ``IntegrationMetaData`` constant
        (the same object the integration's ``IntegrationGateway``
        exposes via ``get_metadata()``). The framework reads
        ``.integration_id`` and ``.label`` from it for shared
        operations like the auto-reconnect pre-pass and the
        entity-removal helper, so each subclass declares the source
        of truth in one place instead of repeating the values at
        every call site."""
        raise NotImplementedError('Subclasses must override this method')

    def get_description(self) -> Optional[str]:
        """One-line operator-facing description of what this
        capability does for this integration. Surfaces in
        capability-specific UI (Content Sources header, future
        per-source descriptions, etc.). Default None — UI omits the
        description when not provided."""
        return None

    def get_attribute_actions_template_name(self) -> Optional[str]:
        """Optional template fragment to render in the integration
        attribute form's action bar. Default None — the action bar
        shows only the framework's free buttons. Subclasses override
        to provide capability-specific actions (status badges,
        lifecycle buttons, etc.)."""
        return None
