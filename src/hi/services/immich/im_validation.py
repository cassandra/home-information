from typing import Dict, List
from urllib.parse import urlparse

from hi.apps.system.enums import HealthStatusType
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    IntegrationKey,
    IntegrationValidationResult,
)

from .enums import ImAttributeType
from .im_metadata import ImmichMetaData


_VALID_SCHEMES = frozenset({ 'http', 'https' })


def validate_attributes(
        integration_attributes : List[ IntegrationAttribute ],
) -> IntegrationValidationResult:
    """Schema-only validation: required attributes present and
    non-empty; API_URL has http(s) scheme and a netloc. Does NOT
    perform network operations."""
    attrs_by_key = _attributes_by_key( integration_attributes )

    api_url = _value( attrs_by_key, ImAttributeType.API_URL )
    if not api_url:
        return IntegrationValidationResult.error(
            status = HealthStatusType.WARNING,
            error_message = f'Missing required attribute: {ImAttributeType.API_URL.label}',
        )

    parsed = urlparse( api_url )
    if parsed.scheme not in _VALID_SCHEMES or not parsed.netloc:
        return IntegrationValidationResult.error(
            status = HealthStatusType.WARNING,
            error_message = (
                f'{ImAttributeType.API_URL.label} must be an http(s) URL '
                f'with a hostname; got {api_url!r}.'
            ),
        )

    api_key = _value( attrs_by_key, ImAttributeType.API_KEY )
    if not api_key:
        return IntegrationValidationResult.error(
            status = HealthStatusType.WARNING,
            error_message = f'Missing required attribute: {ImAttributeType.API_KEY.label}',
        )

    return IntegrationValidationResult.success()


def _attributes_by_key(
        integration_attributes : List[ IntegrationAttribute ],
) -> Dict[ IntegrationKey, IntegrationAttribute ]:
    return { attr.integration_key: attr for attr in integration_attributes }


def _value(
        attrs_by_key : Dict[ IntegrationKey, IntegrationAttribute ],
        attr_type    : ImAttributeType,
) -> str:
    key = IntegrationKey(
        integration_id = ImmichMetaData.integration_id,
        integration_name = str( attr_type ),
    )
    attr = attrs_by_key.get( key )
    if attr is None:
        return ''
    return ( attr.value or '' ).strip()
