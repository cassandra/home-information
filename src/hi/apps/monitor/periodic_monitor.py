import asyncio
import logging


class PeriodicMonitor:
    """
    Base class for any content/information that should be automatically,
    and periodically updated from some external source.
    """

    TRACE = True
    
    def __init__( self, id: str, tag_id: str, interval_secs: int ) -> None:
        self.id = id
        self.tag_id = tag_id
        self.query_interval_secs = interval_secs
        self.query_counter = 0
        self.running = False
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Initialized: {self.__class__.__name__}")
        return

    @property
    def id(self):
        return self.id
    
    async def start(self) -> None:
        self.running = True
        await self.initialize()
        self.logger.info(f"{self.__class__.__name__} started.")
        try:
            while self.running:
                await self.run_query()
                await asyncio.sleep( self.query_interval_secs )
        except asyncio.CancelledError:
            self.logger.info(f"{self.__class__.__name__} stopped.")
        finally:
            await self.cleanup()
        return

    def stop(self) -> None:
        """Stops the monitor."""
        self.running = False
        self.logger.info(f"Stopping {self.__class__.__name__}...")
        return

    async def initialize(self) -> None:
        """
        Optional initialization logic to be implemented by subclasses.
        """
        self.logger.info(f"{self.__class__.__name__} initialized.")
        return
    
    async def run_query(self) -> None:
        self.query_counter += 1
        if self.TRACE:
            self.logger.debug(f"Running query {self.query_counter} for {self.__class__.__name__}")
        try:
            await self.do_periodic_work()
        except Exception as e:
            self.logger.exception(f"Error during query execution: {e}")
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
        self.logger.info(f"{self.__class__.__name__} cleaned up.")
        return

    async def force_wake(self) -> None:
        self.logger.debug(f"Forcing immediate execution of {self.__class__.__name__}")
        await self.run_query()
        return
