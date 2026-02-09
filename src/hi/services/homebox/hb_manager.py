import logging
import threading
from asgiref.sync import sync_to_async
from .pyzm_client.api import ZMApi
from .pyzm_client.helpers.Event import Event as ZmEvent
from .pyzm_client.helpers.Monitor import Monitor as ZmMonitor
from .pyzm_client.helpers.State import State as ZmState
from .pyzm_client.helpers.globals import logger as pyzm_logger
from typing import Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton_manager import SingletonManager
from hi.apps.common.utils import str_to_bool
from hi.apps.system.aggregate_health_provider import AggregateHealthProvider
from hi.apps.system.api_health_status_provider import ApiHealthStatusProvider
from hi.apps.system.provider_info import ProviderInfo
from hi.apps.system.enums import HealthStatusType

from hi.integrations.exceptions import (
    IntegrationAttributeError,
    IntegrationError,
    IntegrationDisabledError,
)
from hi.integrations.transient_models import (
    IntegrationKey,
    IntegrationValidationResult,
)
from hi.integrations.models import Integration, IntegrationAttribute

logger = logging.getLogger(__name__)


class ZoneMinderManager( SingletonManager, AggregateHealthProvider, ApiHealthStatusProvider ):
    def __init_singleton__( self ):
        super().__init_singleton__()  # Initialize _data_lock, _async_data_lock, _was_initialized
        self._zm_attr_type_to_attribute = dict()
        self._client_factory = ZmClientFactory()
        # Thread-local storage for ZMApi clients to avoid session sharing
        self._thread_local = threading.local()

        self._zm_state_list = list()
        self._zm_state_timestamp = datetimeproxy.min()

        self._zm_monitor_list = list()
        self._zm_monitor_timestamp = datetimeproxy.min()

        self._change_listeners = set()

        # Add self as the API health status provider to aggregate
        self.add_api_health_status_provider(self)

        return