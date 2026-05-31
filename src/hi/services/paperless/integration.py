"""Gateway registration entry point for the paperless integration.

EXTERNAL_REFERENCE-only: no Connector, no Importer, no monitors.
The gateway returns the referencer and answers configuration /
access validation; the referencer carries the actual search logic.
"""
import logging
from typing import List, Optional
from urllib.parse import urljoin

import requests

from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationKey,
    IntegrationMetaData,
    IntegrationValidationResult,
)

from .enums import PlAttributeType
from .pl_metadata import PaperlessMetaData
from .pl_models import PaperlessApi
from .pl_referencer import PaperlessExternalReferencer
from .pl_validation import validate_attributes


logger = logging.getLogger(__name__)


class PaperlessGateway( IntegrationGateway ):

    def get_metadata( self ) -> IntegrationMetaData:
        return PaperlessMetaData

    def get_external_referencer( self ) -> PaperlessExternalReferencer:
        return PaperlessExternalReferencer()

    def validate_configuration(
            self,
            integration_attributes : List[ IntegrationAttribute ],
    ) -> IntegrationValidationResult:
        return validate_attributes( integration_attributes )

    def validate_access(
            self,
            integration_attributes : List[ IntegrationAttribute ],
            timeout_secs : Optional[float],
    ) -> ConnectionTestResult:
        """Live access probe: a single tiny request against
        ``/api/documents/?page_size=1`` with the configured auth.
        Returns success on 200; the body is irrelevant."""
        schema_result = validate_attributes( integration_attributes )
        if not schema_result.is_valid:
            return ConnectionTestResult.failure( schema_result.error_message )

        attrs_by_key = {
            attr.integration_key: attr for attr in integration_attributes
        }
        api_url = self._attribute_value( attrs_by_key, PlAttributeType.API_URL )
        token = self._attribute_value( attrs_by_key, PlAttributeType.API_TOKEN )
        # Normalize the same way the client does so the probe matches
        # the runtime behavior.
        normalized = api_url.rstrip('/') + '/'
        probe_url = urljoin( normalized, PaperlessApi.DOCUMENTS_PATH )
        try:
            response = requests.get(
                probe_url,
                params = { PaperlessApi.PAGE_SIZE_PARAM: 1 },
                headers = {
                    PaperlessApi.AUTH_HEADER: f'{PaperlessApi.AUTH_SCHEME} {token}',
                },
                timeout = timeout_secs if timeout_secs is not None else 5.0,
            )
        except requests.RequestException as e:
            return ConnectionTestResult.failure(
                f'Paperless unreachable: {e}'
            )
        if response.status_code == 200:
            return ConnectionTestResult.success()
        if response.status_code in (401, 403):
            return ConnectionTestResult.failure(
                f'Paperless auth rejected (HTTP {response.status_code}).'
            )
        return ConnectionTestResult.failure(
            f'Paperless responded HTTP {response.status_code}.'
        )

    @staticmethod
    def _attribute_value( attrs_by_key, attr_type : PlAttributeType ) -> str:
        key = IntegrationKey(
            integration_id = PaperlessMetaData.integration_id,
            integration_name = str( attr_type ),
        )
        attr = attrs_by_key.get( key )
        if attr is None:
            return ''
        return ( attr.value or '' ).strip()
