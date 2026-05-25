import logging

from hi.integrations.connector.integration_controller import IntegrationController
from hi.integrations.transient_models import IntegrationDetails
from hi.integrations.transient_models import IntegrationControlResult

from .hb_mixins import HomeBoxMixin

logger = logging.getLogger(__name__)


class HomeBoxController( IntegrationController, HomeBoxMixin ):

    def do_control(
        self,
        integration_details: IntegrationDetails,
        hi_control_value: str,
    ) -> IntegrationControlResult:
        logger.debug(
            f'HomeBox do_control unsupported. details={integration_details},'
            f' value={hi_control_value}'
        )
        return IntegrationControlResult(
            new_value = None,
            error_list = [ 'HomeBox control actions are not implemented yet.' ],
        )
