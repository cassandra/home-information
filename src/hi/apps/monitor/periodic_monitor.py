import asyncio
import logging

from hi.apps.system.health_status_provider import HealthStatusProvider


class PeriodicMonitor( HealthStatusProvider ):
    """
    Base class for any content/information that should be automatically,
    and periodically updated from some external source.
    """

    SLEEP_CHUNK_SECS = 10

    def __init__( self, id: str ) -> None:
        self._id = id
        self._query_counter = 0
        self._is_running = False
        self._logger = logging.getLogger(__name__)

        self._logger.debug(f"Initialized: {self.__class__.__name__} with health tracking")
        return

    @property
    def id(self):
        return self._id

    @property
    def is_running(self):
        return self._is_running

    def get_polling_interval_secs(self) -> int:
        """Return the current polling interval in seconds. Subclasses
        must override. The loop calls this each tick before sleeping
        so a value change takes effect on the very next iteration.

        Implementations should be cheap (typically a single attribute
        lookup) -- expensive source-of-truth reads belong in the
        subclass's own cache-and-subscribe code, not here. Static-
        interval monitors return a class constant; dynamic monitors
        return a cache that they keep current via their own listener.
        """
        raise NotImplementedError(
            'Subclasses must implement get_polling_interval_secs()'
        )

    def get_expected_heartbeat_interval_secs(self):
        """A monitor's expected heartbeat is its polling cadence.
        Wires the ``HealthStatusProvider`` hook to the live polling
        value so the expected-interval row in the UI and the dynamic
        staleness thresholds track configuration changes without any
        per-subclass involvement."""
        return self.get_polling_interval_secs()

    async def start(self) -> None:
        self._is_running = True
        self._logger.debug( f"{self.__class__.__name__} async task starting"
                            f" (interval: {self.get_polling_interval_secs()}s)")

        try:
            await self.initialize()
            self._logger.info(f"{self.__class__.__name__} initialized.")
            self.record_healthy( 'Initialized successfully' )
            self._logger.debug( f"{self.__class__.__name__} initialized successfully,"
                                f" entering monitoring loop")

            while self._is_running:
                try:
                    await self.run_query()
                    self.record_heartbeat()

                except Exception as e:
                    self._logger.exception(f"Query execution failed in {self.__class__.__name__}: {e}")
                    self.record_error(f"Query execution failed: {str(e)}")
                    # Continue running despite individual query failures

                self._logger.debug(f"{self.__class__.__name__} entering sleep")
                await self._sleep_until_next_poll()
                self._logger.debug( f"{self.__class__.__name__} woke up,"
                                    f" checking if still running: {self._is_running}")

        except asyncio.CancelledError as ce:
            self._logger.info(f"{self.__class__.__name__} async task cancelled: {ce}")
            self.record_error( "Monitor was cancelled" )
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            self._logger.exception( f"{self.__class__.__name__} async task"
                                    f" failed unexpectedly: {e}")
            self.record_error( f"Monitor failed to start: {str(e)}" )
            raise
        finally:
            await self.cleanup()
            self._logger.info(f"{self.__class__.__name__} async task stopped")
        return

    def stop(self) -> None:
        """Stops the monitor."""
        self._is_running = False
        self._logger.info(f"Stopping {self.__class__.__name__}...")
        return

    async def _sleep_until_next_poll(self) -> None:
        # Sleep in chunks and re-check the configured interval each
        # chunk so a mid-sleep reduction (e.g. 300s -> 5s) takes
        # effect within one chunk rather than waiting out the original
        # interval. An increased interval finishes the current cycle
        # and governs the next one.
        #
        # Operator-visible side effect after a dramatic shrink: the
        # ``HealthStatusProvider``'s expected-heartbeat threshold is
        # now derived live from ``get_polling_interval_secs()``, so
        # immediately after dropping 300s -> 5s the most recent
        # heartbeat (taken under the old cadence, perhaps 200s ago)
        # appears stale against the new threshold and the monitor
        # may briefly read "Dead." The next successful poll
        # (within the new shorter interval) clears it. Not a fault
        # condition; just transient visibility.
        interval_secs = self.get_polling_interval_secs()
        remaining = interval_secs
        while self._is_running:
            if (( remaining <= 0 )
                or ( self.get_polling_interval_secs() < interval_secs )):
                return
            chunk = min( remaining, self.SLEEP_CHUNK_SECS )
            await asyncio.sleep( chunk )
            remaining -= chunk
        return

    async def initialize(self) -> None:
        """
        Optional initialization logic to be implemented by subclasses.
        """
        return
    
    async def run_query(self) -> None:
        self._query_counter += 1
        self._logger.debug(f"Running query {self._query_counter} for {self.__class__.__name__}")

        import hi.apps.common.datetimeproxy as datetimeproxy
        query_start_time = datetimeproxy.now()

        try:
            await self.do_work()
            query_duration = (datetimeproxy.now() - query_start_time).total_seconds()
            self._logger.debug(f"Query {self._query_counter} completed successfully"
                               f" in {query_duration:.2f}s")

            # Log warning if query is taking too long relative to
            # interval. Captured into a local so the threshold check
            # and the message both refer to the same reading.
            interval_secs = self.get_polling_interval_secs()
            if query_duration > (interval_secs * 0.5):
                self._logger.warning(
                    f"Query {self._query_counter} took {query_duration:.2f}s, "
                    f"which is over 50% of the {interval_secs}s interval"
                )

        except Exception as e:
            query_duration = (datetimeproxy.now() - query_start_time).total_seconds()
            # Most monitor failures are recurring upstream-connectivity
            # issues (server down, fault-injection, transient network
            # errors). Logging a full traceback every cycle is noise.
            # Emit a single-line summary at ERROR level and keep the
            # traceback available at DEBUG for when an operator is
            # actively investigating.
            error_message = f"{type(e).__name__}: {e}"
            self._logger.error(
                f"Query {self._query_counter} failed after"
                f" {query_duration:.2f}s: {error_message}"
            )
            self._logger.debug(
                f"Traceback for query {self._query_counter} failure:",
                exc_info=True,
            )
            # Update this monitor's own health status. Without this, the
            # monitor's HealthStatus remains at its prior value (typically
            # HEALTHY) even while every cycle is failing — which both
            # misleads the System Info surface that reads it and
            # suppresses the HealthStatusProvider transition-dispatch
            # path that fires alarms on HEALTHY -> ERROR transitions.
            self.record_error( error_message )
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
