import asyncio
import logging


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
        self._is_running = True
        self._logger.info(f"{self.__class__.__name__} async task starting (interval: {self._query_interval_secs}s)")

        try:
            await self.initialize()
            self._logger.info(f"{self.__class__.__name__} initialized successfully, entering monitoring loop")

            while self._is_running:
                try:
                    await self.run_query()
                except Exception as e:
                    self._logger.exception(f"Query execution failed in {self.__class__.__name__}: {e}")
                    # Continue running despite individual query failures

                # Log sleep phase for debugging hanging issues
                self._logger.debug(f"{self.__class__.__name__} sleeping for {self._query_interval_secs}s")
                await asyncio.sleep(self._query_interval_secs)
                self._logger.debug(f"{self.__class__.__name__} woke up, checking if still running: {self._is_running}")

        except asyncio.CancelledError as ce:
            self._logger.info(f"{self.__class__.__name__} async task cancelled: {ce}")
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            self._logger.exception(f"{self.__class__.__name__} async task failed unexpectedly: {e}")
            raise
        finally:
            self._logger.info(f"{self.__class__.__name__} async task cleaning up")
            await self.cleanup()
            self._logger.info(f"{self.__class__.__name__} async task stopped")
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

        import hi.apps.common.datetimeproxy as datetimeproxy
        query_start_time = datetimeproxy.now()

        try:
            await self.do_work()
            query_duration = (datetimeproxy.now() - query_start_time).total_seconds()
            self._logger.debug(f"Query {self._query_counter} completed successfully in {query_duration:.2f}s")

            # Log warning if query is taking too long relative to interval
            if query_duration > (self._query_interval_secs * 0.5):
                self._logger.warning(f"Query {self._query_counter} took {query_duration:.2f}s, "
                                     f"which is over 50% of the {self._query_interval_secs}s interval")

        except Exception as e:
            query_duration = (datetimeproxy.now() - query_start_time).total_seconds()
            self._logger.exception(f"Query {self._query_counter} failed after {query_duration:.2f}s: {e}")
            # Don't re-raise - the monitor loop in start() will continue despite failures
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
