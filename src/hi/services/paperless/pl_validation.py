"""Configuration validation for the paperless integration.

Shared between the referencer (``validate_configuration``) and the
gateway (``validate_configuration`` + ``validate_access``). Pure
schema-level checks live in ``validate_attributes``; the
network-probing access check is in the gateway proper.
"""
from typing import Dict, List
from urllib.parse import urlparse

from hi.apps.system.enums import HealthStatusType
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    IntegrationKey,
    IntegrationValidationResult,
)

from .enums import PlAttributeType
from .pl_metadata import PaperlessMetaData


_VALID_SCHEMES = frozenset({ 'http', 'https' })


def validate_attributes(
        integration_attributes : List[ IntegrationAttribute ],
) -> IntegrationValidationResult:
    """Schema-only validation: required attributes present and
    non-empty; API_URL has http(s) scheme and a netloc. Does NOT
    perform network operations."""
    attrs_by_key = _attributes_by_key( integration_attributes )

    api_url = _value( attrs_by_key, PlAttributeType.API_URL )
    if not api_url:
        return IntegrationValidationResult.error(
            status = HealthStatusType.WARNING,
            error_message = f'Missing required attribute: {PlAttributeType.API_URL.label}',
        )

    parsed = urlparse( api_url )
    if parsed.scheme not in _VALID_SCHEMES or not parsed.netloc:
        return IntegrationValidationResult.error(
            status = HealthStatusType.WARNING,
            error_message = (
                f'{PlAttributeType.API_URL.label} must be an http(s) URL '
                f'with a hostname; got {api_url!r}.'
            ),
        )

    token = _value( attrs_by_key, PlAttributeType.API_TOKEN )
    if not token:
        return IntegrationValidationResult.error(
            status = HealthStatusType.WARNING,
            error_message = f'Missing required attribute: {PlAttributeType.API_TOKEN.label}',
        )

    return IntegrationValidationResult.success()


def _attributes_by_key(
        integration_attributes : List[ IntegrationAttribute ],
) -> Dict[ IntegrationKey, IntegrationAttribute ]:
    return { attr.integration_key: attr for attr in integration_attributes }


def _value(
        attrs_by_key : Dict[ IntegrationKey, IntegrationAttribute ],
        attr_type    : PlAttributeType,
) -> str:
    key = IntegrationKey(
        integration_id = PaperlessMetaData.integration_id,
        integration_name = str( attr_type ),
    )
    attr = attrs_by_key.get( key )
    if attr is None:
        return ''
    return ( attr.value or '' ).strip()
