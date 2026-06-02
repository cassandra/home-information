"""Shared fault-injection primitives for the simulator.

A single ``FaultMode`` enum and one mode→response mapping, used by both
the services fault middleware and the weather-sources fault middleware.
The fault states are generic HTTP/network failures, identical regardless
of which kind of upstream is being simulated, so there is one definition
here rather than a copy per domain.
"""
import logging
import os
import time

from django.http import HttpResponse, JsonResponse

from hi.apps.common.enums import LabeledEnum

logger = logging.getLogger(__name__)

SLOW_FAULT_SECS = float( os.environ.get( 'HI_SIM_SLOW_FAULT_SECS', '10.0' ) )


class FaultMode( LabeledEnum ):
    """Fault-injection state for a simulated upstream. Selected from the
    simulator UI; consumed by the fault middlewares to short-circuit API
    responses so the main app's failure paths can be exercised without
    standing up a real misbehaving server."""

    HEALTHY = ( 'Healthy', 'Pass requests through normally (default).' )
    AUTH_FAIL = ( 'Auth Fail', 'Return 401 from every API request.' )
    FORBIDDEN = ( 'Forbidden', 'Return 403 from every API request (credentials recognized, action forbidden — e.g., scope or role missing).' )
    SERVER_ERROR = ( 'Server Error', 'Return 500 from every API request.' )
    SLOW = ( 'Slow', 'Sleep past the integration probe timeout, then pass through.' )
    NON_JSON = ( 'Non-JSON', 'Return 200 with text/html body (simulates wrong base URL / proxy).' )

    @classmethod
    def default(cls):
        return cls.HEALTHY


def apply_fault_mode( fault_mode, request, get_response ):
    """Return the response dictated by ``fault_mode``. HEALTHY passes
    through; SLOW sleeps first and then passes through (so the failure
    that surfaces upstream is a read timeout, not a 5xx); the rest return
    a synthetic error response."""
    if fault_mode == FaultMode.AUTH_FAIL:
        return JsonResponse( { 'message': 'Unauthorized' }, status = 401 )
    if fault_mode == FaultMode.FORBIDDEN:
        return JsonResponse( { 'message': 'Forbidden' }, status = 403 )
    if fault_mode == FaultMode.SERVER_ERROR:
        return JsonResponse( { 'message': 'Internal server error' }, status = 500 )
    if fault_mode == FaultMode.SLOW:
        logger.debug( f'Fault injection: sleeping {SLOW_FAULT_SECS}s for {request.path}' )
        time.sleep( SLOW_FAULT_SECS )
        return get_response( request )
    if fault_mode == FaultMode.NON_JSON:
        return HttpResponse(
            b'<html><body>simulated non-JSON response</body></html>',
            content_type = 'text/html',
            status = 200,
        )
    return get_response( request )
