"""Helpers shared by the weather-source simulators.

Deliberately depends only on the standard library, Django, and
``hi.apps.common`` (all of which the simulator settings already
install). The weather simulators must NOT import anything from
``hi.apps.weather`` — the simulator reproduces the upstream wire
format independently, the same way ``nws/constants.py`` hardcodes the
NWS/CAP choice strings instead of importing the main-app enums. The
only contract with the main app is the JSON each endpoint emits and
the ``<SOURCE>_BASE_URL`` setting the operator points at us.
"""
from datetime import date, datetime, timedelta
import json
import random

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

import hi.apps.common.datetimeproxy as datetimeproxy


def jitter( base, amount, index, salt = 0 ):
    """Deterministic pseudo-random offset of ±``amount`` around ``base``.

    Seeded only by ``index`` (plus a per-field ``salt`` so different fields
    don't move in lockstep) — never by time. So forecast series look like
    believable noise that varies period-to-period, stay stable across polls
    (no 20s flicker), and simply recenter when the operator edits the base.
    """
    rng = random.Random( ( ( index + 1 ) * 2654435761 ) ^ ( ( salt + 1 ) * 40503 ) )
    return base + rng.uniform( -amount, amount )


def clamp( value, low, high ):
    return max( low, min( high, value ) )


def render_json_payload( template_name : str, context : dict, encode : bool = False ) -> dict:
    """Render a JSON template file to a parsed dict.

    Templates live in each source app's ``payloads/`` template dir and
    carry ``{{ }}`` placeholders only where the operator gets control.

    With ``encode = False`` (default) the caller supplies already-safe
    primitives and the template quotes strings itself — fine for the
    scalar astronomical payloads. With ``encode = True`` every context
    value is ``json.dumps``-serialized and marked safe, so the template
    uses bare ``{{ x }}`` placeholders for both scalars and arrays; this
    is what the array-heavy Open-Meteo payloads use (a JSON list lands
    in value position without hand-managing commas or quote-escaping).
    """
    if encode:
        context = { key: mark_safe( json.dumps( value ) ) for key, value in context.items() }
    rendered = render_to_string( template_name, context )
    return json.loads( rendered )


def now_hour() -> datetime:
    """Current time truncated to the top of the hour (UTC)."""
    return datetimeproxy.now().replace( minute = 0, second = 0, microsecond = 0 )


def hourly_time_strings( count : int, start : datetime ) -> list:
    """Open-Meteo-style naive hourly timestamps (``YYYY-MM-DDTHH:00``).
    Format matches what the main app uses to locate the current hour."""
    return [ ( start + timedelta( hours = i ) ).strftime( '%Y-%m-%dT%H:00' )
             for i in range( count ) ]


def daily_date_strings( count : int, start : date ) -> list:
    """Open-Meteo-style ``YYYY-MM-DD`` dates for ``count`` consecutive days."""
    return [ ( start + timedelta( days = i ) ).isoformat() for i in range( count ) ]


def date_range_strings( start : date, end : date ) -> list:
    """Inclusive ``YYYY-MM-DD`` list spanning ``start``..``end`` (archive
    requests pass an explicit range)."""
    span = max( 0, ( end - start ).days )
    return [ ( start + timedelta( days = i ) ).isoformat() for i in range( span + 1 ) ]


def parse_request_date( date_str : str ) -> date:
    """The astronomical sources are polled once per day for a run of
    consecutive dates. Echo the requested date back so each day's
    payload is self-consistent; fall back to today on anything
    unparseable."""
    if date_str:
        try:
            return date.fromisoformat( date_str )
        except ValueError:
            pass
    return datetimeproxy.now().date()


def local_hhmm_to_utc_iso( hhmm : str, utc_offset_hours : int, on_date : date ) -> str:
    """Convert an operator-entered local ``HH:MM`` into the UTC ISO
    string shape sources like Sunrise-Sunset.org return (``...+00:00``).

    The main app re-localizes that instant to its own console timezone,
    so to make a time *display* at ``hhmm`` the operator sets
    ``utc_offset_hours`` to their console's UTC offset:
    ``utc = local - offset`` ⇒ ``local = utc + offset``.
    """
    hour, minute = ( int( part ) for part in hhmm.split( ':' ) )
    local_dt = datetime( on_date.year, on_date.month, on_date.day, hour, minute )
    utc_dt = local_dt - timedelta( hours = utc_offset_hours )
    return utc_dt.strftime( '%Y-%m-%dT%H:%M:%S+00:00' )


def shift_utc_iso( utc_iso : str, minutes : int ) -> str:
    """Offset a ``local_hhmm_to_utc_iso`` result by ``minutes`` (used to
    derive twilight boundaries from sunrise/sunset)."""
    base = datetime.strptime( utc_iso, '%Y-%m-%dT%H:%M:%S+00:00' )
    shifted = base + timedelta( minutes = minutes )
    return shifted.strftime( '%Y-%m-%dT%H:%M:%S+00:00' )
