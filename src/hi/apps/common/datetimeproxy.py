# -*- coding: utf-8 -*-
"""
This module should be used for any date or time operations that need to
access the current date or time.  The purpose of forcing all date/time
access through this module is to enable testing of time-specific logic
that requires a specific time to test if it is working.  Tests can
subclass this to override methods to simulate a different wall clock
time than actually exists.
"""

import datetime
import calendar
import pytz
import logging
from email.utils import format_datetime
from email.utils import parsedate_to_datetime

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_TIME_ZONE_NAME = 'America/Chicago'

_time_delta = datetime.timedelta()


def now( tzname = None ):
    """
    Wraps Django's timezone.now() to return a timezone aware
    datetime object.
    """
    global _time_delta

    # This assumes the Django system time is in UTC !!!
    utcnow = timezone.now() + _time_delta
    if tzname is None:
        return utcnow

    try:
        to_zone = pytz.timezone( tzname )
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning( "Unrecognized time zone '%s'", tzname )
        to_zone = pytz.timezone( DEFAULT_TIME_ZONE_NAME )
    
    return utcnow.astimezone(to_zone)


def min( tzname = None ):

    utcmin = datetime.datetime( 1970, 1, 2, tzinfo = pytz.utc )
    if tzname is None:
        return utcmin

    try:
        to_zone = pytz.timezone( tzname )
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning( "Unrecognized time zone '%s'", tzname )
        to_zone = pytz.timezone( DEFAULT_TIME_ZONE_NAME )
    
    return utcmin.astimezone(to_zone)


def is_dst( date_time=None ):
    if date_time is None:
        date_time = now()
    return date_time.dst() != datetime.timedelta(0)

     
def set( force_datetime ):
    global _time_delta
    """
    Sets the current date/time to a specific time.
    """
    _time_delta = force_datetime - timezone.now()
    return


def reset():
    global _time_delta
    _time_delta = datetime.timedelta()
    return


def increment( days=0, seconds=0, microseconds=0,
               milliseconds=0, minutes=0, hours=0, weeks=0 ):
    """
    Incremental the current time by the specified amount.
    """
    global _time_delta
    new_time_delta = datetime.timedelta( days, seconds, microseconds,
                                         milliseconds, minutes, hours, weeks )
    _time_delta = _time_delta + new_time_delta
    return

    
def datetime_to_rfc2822( the_dt = None ):
    """
    Convert a datetime object into a string formatted as RFC 2822
    """
    if not the_dt:
        the_dt = now()
    return format_datetime(the_dt)


def rfc2822_to_datetime(rfc2822_string):
    """
    Parses a date/time string in the RFC 2822 format into a time-aware
    datetime object. Raises ValueError if input string not parsable.
    """
    try:
        the_dt = parsedate_to_datetime(rfc2822_string)

        # If time string has timezone and parsed into a time-aware
        # datetime, then do not force to UTC.
        #
        if the_dt.tzinfo is not None and the_dt.tzinfo.utcoffset(the_dt) is not None:
            return the_dt
        
        # The email.utils module seems to put datetime.timezone.utc in for
        # the tzinfo of the time-aware result, but everytyhing else we do
        # is using the pytz module's version of the UTC timezone.  Hence,
        # we need to force the timezone to match the rest of the code.
        #
        return the_dt.replace(tzinfo=pytz.utc)

    except TypeError:
        raise ValueError( "Could not parse date '%s' as RFC2822" % rfc2822_string )


def from_epoch_secs( epoch_secs, tzname ):
    tzinfo = pytz.timezone( tzname )
    return datetime.datetime.fromtimestamp( epoch_secs, tz=tzinfo )

    
def components_to_datetime_utc( the_date, the_time, tzname ):

    tzinfo = pytz.timezone( tzname )
    naive_dt = datetime.datetime.combine( the_date, the_time )
    local_dt = tzinfo.localize( naive_dt )
    return local_dt.astimezone( pytz.utc )


def week_of_month(dt):
    """ 
    Returns the week of the month for the specified date.
    Assumes a week starts on a Sunday.
    """

    first_day = dt.replace(day=1)
    if first_day.weekday() == 6:
        adjustment = -1
    else:
        adjustment = first_day.weekday()
    return 1 + int( ( dt.day + adjustment ) / 7 )


def elapsed_months( start_date, end_date ):
    """
    Assumes end_date >= start_date.  Only calculates based on
    month setting, not by counting number of days. e.g.,
    There is one month difference between April 30, 2016 and May 1, 2016.
    """
    return ( end_date.year - start_date.year ) * 12 \
        + end_date.month - start_date.month


def add_months( start_dt, num_months ):
    """
    Adds 'num_months' to the start_dt.  If the day of the month does not
    exist for the target month, then the last day of the month is used.
    """
    assert num_months >= 0
    
    # Start by using a zero-based month number (i.e., Jan = 0, Dec = 11)
    month = start_dt.month + num_months - 1
    year = int(start_dt.year + month / 12 )

    # Now convert back to 1-based months
    month = month % 12 + 1

    day = start_dt.day
    max_day = calendar.monthrange(year,month)[1]
    if day > max_day:
        day = max_day

    new_date = datetime.date( year, month, day )
    new_time = start_dt.time()
    new_dt = datetime.datetime.combine( new_date, new_time )
    tzinfo = start_dt.tzinfo
    if tzinfo is None:
        return new_dt
    return tzinfo.localize( new_dt )


def add_years( start_dt, num_years ):
    """
    Adds 'num_months' to the start_dt.  If the day of the month does not
    exist for the target month, then the last day of the month is used.
    """
    assert num_years >= 0
    
    year = start_dt.year + num_years

    new_date = datetime.date( year, start_dt.month, start_dt.day )
    new_time = start_dt.time()
    new_dt = datetime.datetime.combine( new_date, new_time )
    tzinfo = start_dt.tzinfo
    if tzinfo is None:
        return new_dt
    return tzinfo.localize( new_dt )


def date_str_to_date( date_str ):
    """
    The string representation we use to represent a particular day is
    YYYY-MM-DD. This routine and to_date_str() are used in conjunction
    to convert back and forth between the two.
    """
    date_dt = date_str_to_datetime( date_str )
    return date_dt.date()


def date_str_to_datetime( date_str ):
    return datetime.datetime.strptime( date_str, "%Y-%m-%d" )


def date_str_to_datetime_utc( date_str ):
    return date_str_to_datetime( date_str ).replace(tzinfo=pytz.utc)


def to_date_str( date_or_datetime=None ):
    if not date_or_datetime:
        date_or_datetime = now()
    return date_or_datetime.strftime("%Y-%m-%d")


def to_user_date_str( date_or_datetime=None ):
    if not date_or_datetime:
        date_or_datetime = now()
    return date_or_datetime.strftime(settings.DATE_FORMAT)


def time_str_to_time( time_str ):
    ( hour, minute ) = time_str.split('-')
    starts_dt = datetime.datetime( 2000, 1, 2, int(hour), int(minute) )
    return starts_dt.time()


def date_to_datetime_day_begin( the_date, tzname ):
    """
    Convert the date in the given timezone, into a UTC datetime
    that correspsonds to the beginning of the day.
    """
    tzinfo = pytz.timezone( tzname )
    naive_dt = datetime.datetime.combine( the_date, datetime.time.min )
    local_dt = tzinfo.localize( naive_dt )
    return local_dt.astimezone( pytz.utc )


def date_to_datetime_day_end( the_date, tzname ):
    """
    Convert the date in the given timezone, into a UTC datetime
    that correspsonds to the beginning of the day.
    """
    tzinfo = pytz.timezone( tzname )
    naive_dt = datetime.datetime.combine( the_date, datetime.time.max )
    local_dt = tzinfo.localize( naive_dt )
    return local_dt.astimezone( pytz.utc )


def date_to_datetime_range_tuple( the_date, tzinfo=None ):
    """
    Return a tuple that represnts the datetime beginning and ending of
    the given date, making an "aware" datetime if a timezone is given.
    """
    
    dt_min = datetime.datetime.combine( the_date, datetime.time.min )
    dt_max = datetime.datetime.combine( the_date, datetime.time.max )

    if tzinfo is not None:
        dt_min = tzinfo.localize( dt_min )
        dt_max = tzinfo.localize( dt_max )

    return ( dt_min, dt_max )


def get_today_view_range( selected_dt : datetime.datetime  = None ):
    if not selected_dt:
        selected_dt = now()
    start_date = selected_dt.date()
    end_date = start_date
    return ( start_date, end_date )


def get_yesterday_view_range( selected_dt : datetime.datetime  = None ):
    if not selected_dt:
        selected_dt = now()
    start_date = selected_dt.date() - datetime.timedelta( days = 1 )
    end_date = start_date
    return ( start_date, end_date )
       

def get_weekly_view_range( selected_dt : datetime.datetime  = None ):
    """ Given any arbitrary date/time, this find the bounding week """

    if not selected_dt:
        selected_dt = now()
        
    # Always start on Sunday (0=Monday)
    start_date = selected_dt.date()

    # Always start on Sunday (0=Monday)
    weekday = start_date.weekday()
    if weekday < 6:
        delta_days = weekday + 1
        delta_datetime = datetime.timedelta( days = delta_days )
        start_date = start_date - delta_datetime

    delta_datetime = datetime.timedelta( days = 6 )
    end_date = start_date + delta_datetime

    return ( start_date, end_date )


def get_monthly_view_range( selected_dt : datetime.datetime  = None ):
    """
    The month view usually includes some number of days in the
    preceding and following months.
    """
    if not selected_dt:
        selected_dt = now()

    # Returns weekday of first day of the month and number of days in
    # month, for the specified year and month.
    #
    ( weekday, num_days ) = calendar.monthrange( selected_dt.year,
                                                 selected_dt.month )

    start_date = datetime.date( selected_dt.year, 
                                selected_dt.month,
                                1 )

    end_date = datetime.date( selected_dt.year, 
                              selected_dt.month, 
                              num_days )

    return ( start_date, end_date )


def month_name_year_to_datetime( date_str : str ):
    return datetime.datetime.strptime( date_str, "%B %Y" )


def day_month_name_year_to_datetime( date_str : str ):
    return datetime.datetime.strptime( date_str, "%d %B %Y" )


def year_to_datetime( date_str : str ):
    return datetime.datetime.strptime( date_str, "%Y" )


def iso_naive_to_datetime_utc( iso_str : str, tzname : str = 'UTC' ):
    to_zone = pytz.timezone( tzname )
    naive_time = datetime.datetime.fromisoformat( iso_str )
    aware_time = to_zone.localize(naive_time)
    utc_time = aware_time.astimezone( pytz.UTC )
    return utc_time


def change_timezone( original_datetime : datetime, new_tzname : str  ):
    try:
        new_tz = pytz.timezone( new_tzname )
        return original_datetime.astimezone( new_tz )
    except pytz.exceptions.UnknownTimeZoneError:
        return original_datetime.astimezone( DEFAULT_TIME_ZONE_NAME )
    

def get_since_time_humanized( reference_datetime : datetime ):
    current_datetime = now()
    elapsed_timedelta = current_datetime - reference_datetime
    elapsed_seconds = elapsed_timedelta.total_seconds()
    if elapsed_seconds < 55:
        return f'{round(elapsed_seconds)} seconds ago'
    
    elapsed_minutes = elapsed_seconds / 60
    
    if elapsed_minutes <= 90:
        return f'{round(elapsed_minutes)} minutes ago'

    elapsed_hours = elapsed_minutes / 60
    if elapsed_hours <= 24:
        return f'over {round(elapsed_hours)} hours ago'

    return reference_datetime.strftime('%A, %B %d at %I:%M %p')


def is_time_of_day_in_interval( time_of_day_str  : str,
                                tz_name          : str,
                                start_datetime   : datetime,
                                end_datetime     : datetime  ) -> bool:

    target_datetime_unaware = datetime.datetime.strptime( time_of_day_str, "%H:%M" )
    target_time = target_datetime_unaware.time()

    timezone = pytz.timezone( tz_name )
    start_datetime_tz = start_datetime.astimezone( timezone )
    end_datetime_tz = end_datetime.astimezone( timezone )

    today = start_datetime_tz.date()
    target_datetime_tz = timezone.localize( datetime.datetime.combine( today, target_time ) )

    return bool(( target_datetime_tz > start_datetime_tz ) and ( target_datetime_tz <= end_datetime_tz ))


def is_valid_timezone_name( tz_name : str ) -> bool:
    return tz_name in pytz.all_timezones_set
