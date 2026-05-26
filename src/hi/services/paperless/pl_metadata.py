from hi.integrations.enums import IntegrationCapability
from hi.integrations.transient_models import IntegrationMetaData

from .enums import PlAttributeType


PaperlessMetaData = IntegrationMetaData(
    # ``paperless`` (not ``paperless-ngx``) for internal naming, in
    # line with how zoneminder / homebox use the short form. The
    # human label keeps the ``-ngx`` suffix.
    integration_id = 'paperless',
    label = 'Paperless-ngx',
    attribute_type = PlAttributeType,
    # Paperless documents become TEXT attributes on existing
    # Entity / Location records via ATTRIBUTE_REFERENCE; the
    # integration never creates HI Entities of its own, so deletion
    # behavior is moot. Internal attributes (those created by HI
    # outside the integration's settings) are not supported here.
    allow_entity_deletion = False,
    allow_internal_attributes = False,
    logo_static_path = 'img/integrations/paperless.png',
    capabilities = frozenset({
        IntegrationCapability.ATTRIBUTE_REFERENCE,
    }),
)
