import logging
import os
from django.core.signals import request_started

from hi.apps.common.asyncio_utils import start_background_event_loop
from hi.apps.monitor.monitor_manager import AppMonitorManager
from hi.integrations.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)


class HiBackgroundTaskHelper:

    _request_started_connect = False
    _background_requests_started = False
    
    @classmethod
    def start_background_tasks_delayed(cls):
        """
        Delay starting background tasks until first user request. Adds latency,
        but the most reliable way to ensure Dajngo is fully configure.  You
        can't launch these in APpConfig.ready() as Django is not actualy
        quite "ready" and new threads will fail.  You cannot add a delay
        with time.sleep() because that also interferes with Django's
        initialization process.  Deferring until the first request is the
        lesser of all the evils.
        """
        if cls.is_management_command():
            return
        if cls._request_started_connect:
            return
        request_started.connect( lambda sender, **kwargs: cls.start_background_tasks() )
        cls._request_started_connect = True
        return
    
    @classmethod
    def start_background_tasks(cls):
        if cls.is_management_command():
            return
        
        if cls._request_started_connect:
            request_started.disconnect( lambda sender, **kwargs: cls.start_background_tasks() )
            cls._request_started_connect = False

        if cls._background_requests_started:
            return
        
        logger.info( 'Starting AppMonitorManager ...' )
        start_background_event_loop(
            task_function = AppMonitorManager().initialize,
            pass_event_loop = True,
        ) 
        
        logger.info( 'Starting IntegrationManager ...' )
        start_background_event_loop(
            task_function = IntegrationManager().initialize,
            pass_event_loop = True,
        ) 

        cls._background_requests_started = True
        return

    @classmethod
    def is_management_command(cls) -> bool:
        return bool( os.environ.get('DJANGO_MANAGEMENT_COMMAND') is not None )
    
