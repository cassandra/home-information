from typing import List, Optional

from hi.integrations.connector.integration_connector import IntegrationConnector
from hi.integrations.importer.integration_importer import IntegrationImporter
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)


class IntegrationGateway:
    """
    Each integration needs to provide an Integration Manager that implements these methods.
    """

    def get_metadata(self) -> IntegrationMetaData:
        raise NotImplementedError('Subclasses must override this method')

    def notify_settings_changed(self):
        """
        This method is called when Integration or IntegrationAttribute models
        are modified. Each integration should implement this to reload its
        configuration and notify any dependent components.
        """
        raise NotImplementedError('Subclasses must override this method')

    def get_connector(self) -> Optional[IntegrationConnector]:
        """
        Return the integration's connector when it supports sync;
        None otherwise. Sync is an opt-in capability — not every
        integration requires one. The framework owns the sync workflow
        (pre-sync confirmation, sync execution, post-sync placement);
        the connector participates by providing the integration-
        specific work plus a small amount of peripheral metadata.

        The Issue #283 sync-check probe also rides on the connector
        (see ``IntegrationConnector.check_needs_sync``): integrations
        without a connector naturally opt out of both full sync and
        the periodic drift check.
        """
        return None

    def get_importer(self) -> Optional[IntegrationImporter]:
        """
        Return the integration's importer when it supports the IMPORT
        capability; None otherwise. Parallel to get_connector() for
        the CONNECT capability. The framework owns the import workflow
        (Data Import page, preview, confirm, result modal, placement);
        the importer supplies the integration-specific candidate
        listing, item ingest, and discard operations.
        """
        return None

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """
        Schema-only validation of the proposed configuration. Must NOT
        perform network operations. Returns success if the attribute set
        is structurally usable; returns an error otherwise. For live
        access validation, see validate_access().
        """
        raise NotImplementedError('Subclasses must override this method')

    def validate_access(
            self,
            integration_attributes: List[IntegrationAttribute],
            timeout_secs: Optional[float],
    ) -> ConnectionTestResult:
        """
        Live probe to validate access to the upstream system using the
        proposed configuration. Must respect the bounded timeout. Used
        at attribute-save time (Configure / Reconfigure) and before
        relaunching monitors (Resume).
        """
        raise NotImplementedError('Subclasses must override this method')
