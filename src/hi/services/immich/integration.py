import logging
from typing import List, Optional
from urllib.parse import urljoin

import requests

from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.models import IntegrationAttribute
from hi.integrations.referencer.integration_referencer import (
    IntegrationExternalReferencer,
)
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationKey,
    IntegrationMetaData,
    IntegrationValidationResult,
)

from .enums import ImAttributeType
from .im_metadata import ImmichMetaData
from .im_models import ImmichApi
from .im_referencer import ImmichExternalReferencer
from .im_validation import validate_attributes


logger = logging.getLogger(__name__)


class ImmichGateway( IntegrationGateway ):

    def get_metadata( self ) -> IntegrationMetaData:
        return ImmichMetaData

    def get_external_referencer( self ) -> IntegrationExternalReferencer:
        return ImmichExternalReferencer()

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
        """Live access probe: ``POST /api/search/metadata`` with body
        ``{"size": 1}``. The metadata endpoint is cheap (no CLIP
        embedding) and exercises the same ``asset.read`` scope the
        referencer needs at search time, so a green probe predicts a
        working integration. Returns success on 200, distinguishing
        401 (unrecognized key) from 403 (key lacks ``asset.read``) so
        operators can fix the right thing."""
        schema_result = validate_attributes( integration_attributes )
        if not schema_result.is_valid:
            return ConnectionTestResult.failure( schema_result.error_message )

        attrs_by_key = {
            attr.integration_key: attr for attr in integration_attributes
        }
        api_url = self._attribute_value( attrs_by_key, ImAttributeType.API_URL )
        api_key = self._attribute_value( attrs_by_key, ImAttributeType.API_KEY )
        normalized = api_url.rstrip('/') + '/'
        probe_url = urljoin( normalized, ImmichApi.SEARCH_METADATA_PROBE_PATH )
        try:
            response = requests.post(
                probe_url,
                json = { ImmichApi.REQUEST_SIZE: 1 },
                headers = { ImmichApi.AUTH_HEADER: api_key },
                timeout = timeout_secs if timeout_secs is not None else 5.0,
            )
        except requests.RequestException as e:
            return ConnectionTestResult.failure(
                f'Immich unreachable: {e}'
            )
        if response.status_code == 200:
            return ConnectionTestResult.success()
        if response.status_code == 401:
            return ConnectionTestResult.failure(
                'Immich API key not recognized (HTTP 401). Check the '
                'key value, or create a new key in Immich → Account '
                'Settings → API Keys.'
            )
        if response.status_code == 403:
            return ConnectionTestResult.failure(
                'Immich API key is missing the asset.read permission '
                '(HTTP 403). Re-create the key in Immich → Account '
                'Settings → API Keys with asset.read granted.'
            )
        return ConnectionTestResult.failure(
            f'Immich responded HTTP {response.status_code}.'
        )

    @staticmethod
    def _attribute_value( attrs_by_key, attr_type : ImAttributeType ) -> str:
        key = IntegrationKey(
            integration_id = ImmichMetaData.integration_id,
            integration_name = str( attr_type ),
        )
        attr = attrs_by_key.get( key )
        if attr is None:
            return ''
        return ( attr.value or '' ).strip()
