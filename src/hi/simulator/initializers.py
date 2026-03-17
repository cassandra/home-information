import logging

from django.db import transaction

import hi.apps.common.datetimeproxy as datetimeproxy

from .models import SimProfile
from .simulator_manager import SimulatorManager

logger = logging.getLogger(__name__)


class SimulatorInitializer:
    """Ensure required Simulator DB records exist after migrations are applied."""

    def run( self, sender = None, **kwargs ):
        logger.debug( 'Populating initial DB records for simulator.' )
        self._create_default_profile_if_needed()
        return

    def _create_default_profile_if_needed( self ):
        with transaction.atomic():
            _current_sim_profile = SimProfile.objects.all().first()
            if _current_sim_profile:
                return

            SimProfile.objects.create(
                name = SimulatorManager.DEFAULT_PROFILE_NAME,
                last_switched_to_datetime = datetimeproxy.now(),
            )
        return
