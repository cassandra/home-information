import asyncio
import logging


class PeriodicMonitor:
    """
    Base class for any content/information that should be automatically,
    and periodically updated from some external source.
    """

    TRACE = True
    
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
        self._is_running = True
        await self.initialize()
        self._logger.info(f"{self.__class__.__name__} started.")
        try:
            while self._is_running:
                await self.run_query()
                await asyncio.sleep( self._query_interval_secs )
        except asyncio.CancelledError:
            self._logger.info(f"{self.__class__.__name__} stopped.")
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
        if self.TRACE:
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
