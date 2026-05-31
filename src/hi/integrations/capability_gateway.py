"""Common base for the per-capability gateway peers.

``IntegrationConnector``, ``IntegrationImporter``, and
``IntegrationExternalReferencer`` are the three per-capability
gateway classes today: each is the framework-facing surface for a
specific ``IntegrationCapability``.

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

    capability: IntegrationCapability

    def get_metadata(self) -> IntegrationMetaData:
        """Return the integration's ``IntegrationMetaData`` constant --
        the same object the integration's ``IntegrationGateway`` exposes
        via ``get_metadata()``. Declared per subclass so the framework can
        read the integration's identity from a single source."""
        raise NotImplementedError('Subclasses must override this method')

    def get_description(self) -> Optional[str]:
        """One-line operator-facing description of what this capability
        does for this integration, surfaced in capability-specific UI.
        Default None -- UI omits the description when not provided."""
        return None

    def get_attribute_actions_template_name(self) -> Optional[str]:
        """Optional template fragment to render in the integration
        attribute form's action bar. Default None -- the action bar shows
        only the framework's free buttons."""
        return None
