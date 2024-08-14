import datetime
import logging
import pytz
import unittest

from django.utils import timezone

import waa.apps.common.datetimeproxy as datetimeproxy

logging.disable(logging.CRITICAL)


class TestDateTimeProxy(unittest.TestCase):

    def test_basic(self):

        ##########
        # Ensure unaltered time matches real system time
        proxy_dt = datetimeproxy.reset()
        native_dt = timezone.now()
        proxy_dt = datetimeproxy.now()
        delta = proxy_dt - native_dt
        self.assertTrue( delta.total_seconds() <= 1 )

        ##########
        # Setting specific time in the future

        proxy_dt = datetimeproxy.reset()
        native_dt = timezone.now()
        future_dt = native_dt + datetime.timedelta( hours=5 )
        datetimeproxy.set( future_dt )
        proxy_dt = datetimeproxy.now()
        delta = proxy_dt - native_dt
        self.assertTrue( delta.total_seconds() >= (5*60*60-1) )
        self.assertTrue( delta.total_seconds() <= (5*60*60+1) )
        
        ##########
        # Setting specific time in the past

        proxy_dt = datetimeproxy.reset()
        native_dt = timezone.now()
        future_dt = native_dt + datetime.timedelta( hours=-5 )
        datetimeproxy.set( future_dt )
        proxy_dt = datetimeproxy.now()
        delta = proxy_dt - native_dt
        self.assertTrue( -1*delta.total_seconds() >= (5*60*60-1) )
        self.assertTrue( -1*delta.total_seconds() <= (5*60*60+1) )

        ##########
        # Incrementing time forward

        proxy_dt = datetimeproxy.reset()
        native_dt = timezone.now()
        datetimeproxy.increment( hours=8 )
        proxy_dt = datetimeproxy.now()
        delta = proxy_dt - native_dt
        self.assertTrue( delta.total_seconds() >= (8*60*60-1) )
        self.assertTrue( delta.total_seconds() <= (8*60*60+1) )
        
        ##########
        # Incrementing time backward
        
        proxy_dt = datetimeproxy.reset()
        native_dt = timezone.now()
        datetimeproxy.increment( hours=-8 )
        proxy_dt = datetimeproxy.now()
        delta = proxy_dt - native_dt
        self.assertTrue( -1*delta.total_seconds() >= (8*60*60-1) )
        self.assertTrue( -1*delta.total_seconds() <= (8*60*60+1) )
        
        return

    def test_timezones(self):

        ##########
        # Timezones error handling - Fallback to central time
            
        localnow = datetimeproxy.now('')
        if datetimeproxy.is_dst(localnow):
            expect_tzname = 'CDT'
        else:
            expect_tzname = 'CST'
        self.assertEqual( expect_tzname, localnow.tzname() )
        localnow = datetimeproxy.now('    ')
        if datetimeproxy.is_dst(localnow):
            expect_tzname = 'CDT'
        else:
            expect_tzname = 'CST'
        self.assertEqual( expect_tzname, localnow.tzname() )
        localnow = datetimeproxy.now('BAD/TIME_ZONE')
        if datetimeproxy.is_dst(localnow):
            expect_tzname = 'CDT'
        else:
            expect_tzname = 'CST'
        self.assertEqual( expect_tzname, localnow.tzname() )
        
        ##########
        # Ensuring timezones working for common cases
        
        proxy_dt = datetimeproxy.reset()
        localnow = datetimeproxy.now('America/New_York')
        delta_secs = localnow.utcoffset().total_seconds()
        min_secs =  -1 * 4 * 60 * 60 + 2 # EDT
        max_secs = -1 * 5 * 60 * 60 - 2  # EST
        self.assertTrue( (( delta_secs < min_secs )
                          and ( delta_secs > max_secs )))
        
        localnow = datetimeproxy.now('America/Chicago')
        delta_secs = localnow.utcoffset().total_seconds()
        min_secs =  -1 * 5 * 60 * 60 + 2 # CDT
        max_secs = -1 * 6 * 60 * 60 - 2  # CST
        self.assertTrue( (( delta_secs < min_secs )
                          and ( delta_secs > max_secs )))

        ##########
        # Ensure time of day shows up relative to timezone
        naive_dt = datetime.datetime( year=2016, month=3, day=29,
                                   hour=17, minute=12, second=12 )
        tzinfo = pytz.timezone('UTC')
        force_dt = tzinfo.localize(naive_dt)
        datetimeproxy.set( force_dt )

        local_now = datetimeproxy.now( 'America/Chicago' )
        local_now.time()

        # Account for daylight savings time
        self.assertTrue( ( 12 == local_now.hour ) or ( 11 == local_now.hour ))
        
        return
        
    def test_rfc2822_conversions(self):
        
        naive_dt = datetime.datetime( year=2016, month=3, day=29,
                                   hour=17, minute=12, second=12 )
        tzinfo = pytz.timezone('UTC')
        the_dt = tzinfo.localize(naive_dt)

        rfc2822_string = datetimeproxy.datetime_to_rfc2822( the_dt )
        self.assertEqual( 'Tue, 29 Mar 2016 17:12:12 +0000', rfc2822_string )

        result_dt = datetimeproxy.rfc2822_to_datetime( rfc2822_string )
        self.assertEqual( the_dt, result_dt )
        return

        
    def test_week_of_month(self):

        dt = datetime.date( 2016, 11, 1 )
        self.assertEqual( 1, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2016, 11, 5 )
        self.assertEqual( 1, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2016, 11, 6 )
        self.assertEqual( 2, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2016, 11, 12 )
        self.assertEqual( 2, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2016, 11, 13 )
        self.assertEqual( 3, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2016, 11, 14 )
        self.assertEqual( 3, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2016, 11, 30 )
        self.assertEqual( 5, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2016, 12, 3 )
        self.assertEqual( 1, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2016, 12, 4 )
        self.assertEqual( 2, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2016, 12, 31 )
        self.assertEqual( 5, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2017, 1, 1 )
        self.assertEqual( 1, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2017, 1, 7 )
        self.assertEqual( 1, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2017, 1, 8 )
        self.assertEqual( 2, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2017, 1, 28 )
        self.assertEqual( 4, datetimeproxy.week_of_month( dt ))

        dt = datetime.date( 2017, 1, 29 )
        self.assertEqual( 5, datetimeproxy.week_of_month( dt ))

        dt = datetime.datetime( 2016, 11, 13, 1, 0, 0 )
        self.assertEqual( 3, datetimeproxy.week_of_month( dt ))

        return

    def test_date_to_datetime(self):
        
        the_date = datetime.date( 2016, 11, 12 )
        dt = datetimeproxy.date_to_datetime_day_begin( the_date, 'US/Central' )
        self.assertEqual( 2016, dt.year )
        self.assertEqual( 11, dt.month )
        self.assertEqual( 12, dt.day )
        self.assertEqual( 6, dt.hour )
        self.assertEqual( 0, dt.minute )

        the_date = datetime.date( 2016, 11, 12 )
        dt = datetimeproxy.date_to_datetime_day_end( the_date, 'US/Central' )
        self.assertEqual( 2016, dt.year )
        self.assertEqual( 11, dt.month )
        self.assertEqual( 13, dt.day )
        self.assertEqual( 5, dt.hour )
        self.assertEqual( 59, dt.minute )
        return

    def test_elapsed_months(self):

        start = datetime.date( 2016, 11, 29 )
        end = datetime.date( 2016, 11, 30 )
        self.assertEqual( 0, datetimeproxy.elapsed_months( start, end ))

        start = datetime.date( 2016, 11, 29 )
        end = datetime.date( 2016, 12, 1 )
        self.assertEqual( 1, datetimeproxy.elapsed_months( start, end ))
 
        start = datetime.date( 2016, 11, 29 )
        end = datetime.date( 2017, 1, 1 )
        self.assertEqual( 2, datetimeproxy.elapsed_months( start, end ))

        start = datetime.date( 2016, 11, 29 )
        end = datetime.date( 2017, 12, 5 )
        self.assertEqual( 13, datetimeproxy.elapsed_months( start, end ))

        return
    
    def test_add_months(self):

        ##########
        with self.assertRaises( AssertionError ):
            start_dt = datetime.datetime( 2016, 11, 29, 8, 5, 0 )
            datetimeproxy.add_months( start_dt, -1 )

        ##########
        tzinfo = pytz.timezone('US/Eastern')
        start_dt = datetime.datetime( 2016, 11, 29, 8, 5, 0 )
        start_dt = tzinfo.localize( start_dt )
        
        new_dt = datetimeproxy.add_months( start_dt, 1 )
        self.assertEqual( 2016, new_dt.year )
        self.assertEqual( 12, new_dt.month )
        self.assertEqual( 29, new_dt.day )
        self.assertEqual( 8, new_dt.hour )
        self.assertEqual( 5, new_dt.minute )
        self.assertEqual( start_dt.tzname(), new_dt.tzname() )
        
        ##########
        tzinfo = pytz.timezone('UTC')
        start_dt = datetime.datetime( 2016, 11, 29, 8, 5, 0 )
        start_dt = tzinfo.localize( start_dt )

        new_dt = datetimeproxy.add_months( start_dt, 2 )
        self.assertEqual( 2017, new_dt.year )
        self.assertEqual( 1, new_dt.month )
        self.assertEqual( 29, new_dt.day )
        self.assertEqual( 8, new_dt.hour )
        self.assertEqual( 5, new_dt.minute )
        self.assertEqual( start_dt.tzname(), new_dt.tzname() )
        
        ##########
        start_dt = datetime.datetime( 2016, 11, 29, 8, 5, 0 )
        new_dt = datetimeproxy.add_months( start_dt, 3 )
        self.assertEqual( 2017, new_dt.year )
        self.assertEqual( 2, new_dt.month )
        self.assertEqual( 28, new_dt.day )
        self.assertEqual( 8, new_dt.hour )
        self.assertEqual( 5, new_dt.minute )
        self.assertEqual( start_dt.tzname(), new_dt.tzname() )
        
        ##########
        start_dt = datetime.datetime( 2016, 11, 30, 8, 5, 0 )
        new_dt = datetimeproxy.add_months( start_dt, 87 )
        self.assertEqual( 2024, new_dt.year )
        self.assertEqual( 2, new_dt.month )
        self.assertEqual( 29, new_dt.day )
        self.assertEqual( 8, new_dt.hour )
        self.assertEqual( 5, new_dt.minute )
        self.assertEqual( start_dt.tzname(), new_dt.tzname() )
        
        return
    
