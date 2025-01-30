import asyncio
import logging

import hi.apps.common.debug_utils as debug_utils


class PeriodicMonitor:
    """
    Base class for any content/information that should be automatically,
    and periodically updated from some external source.
    """

    def __init__( self, id: str, interval_secs: int ) -> None:
        self._id = id
        self._query_interval_secs = interval_secs
        self._query_counter = 0
        self._is_running = False
        self._logger = logging.getLogger(__name__)
        self._logger.debug(f"Initialized: {self.__class__.__name__}")
        return

    @property
    def id(self):
        return self._id

    @property
    def is_running(self):
        return self._is_running
    
    async def start(self) -> None:

        print( 'PERIODIC START' )
    


        
        self._is_running = True
        await self.initialize()
        self._logger.info(f"{self.__class__.__name__} started.")
        try:
            while self._is_running:

                
                print( 'PRE_ALERT_QUERY' )
    

                await self.run_query()

                
                print( f'POST_ALERT_QUERY: %s' % debug_utils.get_event_loop_context() )



                
                try:
                    await asyncio.sleep(self._query_interval_secs)
                except asyncio.CancelledError:
                    logger.warning("Task was cancelled! Cleaning up...")
                    # Perform any necessary cleanup (e.g., closing connections)
                    return  # Or raise the exception if you want it to propagate
                except Exception as e: # Catch other exceptions
                    logger.exception(f"An unexpected error occurred: {e}")
                    # Handle the error appropriately (e.g., log, retry, etc.)

                print( 'POST_ALERT_SELEEP' )



                    
                await asyncio.sleep( self._query_interval_secs )

                print( 'POST_ALERT_SELEEP' )
    
        except asyncio.CancelledError as ce:
            self._logger.exception( 'Monitor cancelled' )
            self._logger.info(f"{self.__class__.__name__} stopped. ({ce})")
        finally:
            await self.cleanup()
        return

    def stop(self) -> None:
        """Stops the monitor."""
        self._is_running = False
        self._logger.info(f"Stopping {self.__class__.__name__}...")
        return

    async def initialize(self) -> None:
        """
        Optional initialization logic to be implemented by subclasses.
        """
        self._logger.info(f"{self.__class__.__name__} initialized.")
        return
    
    async def run_query(self) -> None:
        self._query_counter += 1
        self._logger.debug(f"Running query {self._query_counter} for {self.__class__.__name__}")
        try:
            await self.do_work()
        except Exception as e:
            self._logger.exception(f"Error during query execution: {e}")
        return

    async def do_work(self) -> None:
        """
        Abstract method for subclasses to implement specific periodic logic.
        """
        raise NotImplementedError("Subclasses must implement do_work()")

    async def cleanup(self) -> None:
        """
        Optional cleanup logic to be implemented by subclasses.
        """
        self._logger.info(f"{self.__class__.__name__} cleaned up.")
        return

    async def force_wake(self) -> None:
        self._logger.debug(f"Forcing immediate execution of {self.__class__.__name__}")
        await self.run_query()
        return
