import hashlib
import os
import re
from typing import Tuple
from urllib import parse as urllib_parse

from django.conf import settings
from django.http import HttpRequest

from . import profanity


def is_ajax( request : HttpRequest ):
    return bool( request.headers.get('x-requested-with') == 'XMLHttpRequest' )


def is_blank( obj ):
    if obj is None:
        return True
    if not isinstance( obj, str ):
        return False
    return bool( obj.strip() == '' )


def str_to_bool( value: str ) -> bool:
    truthy_values = {'true', '1', 'on', 'yes', 'y', 't', 'enabled'}
    if isinstance( value, str ):
        return value.strip().lower() in truthy_values
    return False


def get_long_display_name( user_obj ):
    if not user_obj:
        return settings.USER_DISPLAY_NAME_DEFAULT
    if user_obj.last_name and user_obj.first_name:
        return '%s, %s' % ( user_obj.last_name, user_obj.first_name )
    if user_obj.last_name:
        return user_obj.last_name
    if user_obj.first_name:
        return user_obj.first_name
    return re.sub( r'\@.+$', '', user_obj.email )


def get_short_display_name( user_obj ):
    if not user_obj or user_obj.is_anonymous:
        return settings.USER_DISPLAY_NAME_DEFAULT
    if user_obj.first_name:
        return user_obj.first_name[0:20]
    if user_obj.last_name:
        return user_obj.last_name[0:20]
    return re.sub( r'\@.+$', '', user_obj.email )
 

def get_absolute_static_path( relative_path ):
    return os.path.join( settings.STATIC_URL, relative_path )


def get_humanized_secs( sec_elapsed ):

    if sec_elapsed < 1:
        return '0 secs'
    
    days = int(sec_elapsed / (24 * 60 * 60))
    hours = int(sec_elapsed % (24 * 60 * 60) / (60 * 60))
    minutes = int((sec_elapsed % (60 * 60)) / 60)
    seconds = int(sec_elapsed % 60.0)

    components = []
    if days > 1:
        components.append( f'{days} days' )
    elif days > 0:
        components.append( f'{days} day' )

    if hours > 1:
        components.append( f'{hours} hrs' )
    elif hours > 0:
        components.append( f'{hours} hr' )
        
    if minutes > 1:
        components.append( f'{minutes} mins' )
    elif minutes > 0:
        components.append( f'{minutes} min' )

    if seconds > 1:
        components.append( f'{seconds} secs' )
    elif seconds > 0:
        components.append( f'{seconds} sec' )

    return ', '.join( components )


def get_humanized_number( value ):
    if value == 0:
        return 'zero'
    if (( value % 100 ) > 10 ) and (( value % 100 ) < 20 ):
        return f'{value:,}th'
    if ( value % 10 ) == 1:
        return f'{value:,}st'
    if ( value % 10 ) == 2:
        return f'{value:,}nd'
    if ( value % 10 ) == 3:
        return f'{value:,}rd'
    return f'{value:,}th'


def is_profanity_text( text ):
    if not text:
        return False
    for word in re.split( r'[\W]+', text ):
        if word.lower() in profanity.PROFANITY_WORDS:
            return True
        continue
    return False


def url_simplify( text : str ):
    """ For creating readable, but simple url labels from text. """
    if not text:
        return ''
    return re.sub( r'[\W]+', '-', text.lower() ).rstrip('-').lstrip('-')
        

def hash_with_seed( value : str ):
    """
    Hash a string in a moderately secure way using a seed value that someone
    has to have access to. most used to support email unsubscribing without
    the need to login.
    """
    seed = settings.SECRET_KEY
    m = hashlib.sha256()
    m.update( seed.encode('utf-8') )
    m.update( str(value).encode('utf-8') )
    return m.hexdigest()


REPLACE_URL_REGEX = re.compile( r"((https?):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)",
                                re.MULTILINE | re.UNICODE )


def replace_url_text_with_html_anchor( value : str, use_link_text : bool = True ):
    if not value:
        return value
    try:
        if use_link_text:
            value = REPLACE_URL_REGEX.sub(r'<a href="\1" target="_blank">LINK</a>', value)
        else:
            value = REPLACE_URL_REGEX.sub(r'<a href="\1" target="_blank">\1</a>', value)
        return value
    
    except Exception:
        # We never want this to fail and do not care that much if it does.
        return value

    
def get_url_top_level_domain( url_str : str, default_value : str = None ):

    hostname = urllib_parse.urlparse( url_str ).hostname
    if not hostname:
        return default_value
    
    parts = hostname.split('.')
    if len(parts) < 2:
        return default_value
    
    if len(parts) < 3:
        return hostname

    return f'{parts[-2]}.{parts[-1]}'


def jaccard_coefficient( interval_1 : Tuple[ int, int ], interval_2 : Tuple[ int, int ] ):

    intersection = max(0, min( interval_1[1], interval_2[1]) - max(interval_1[0], interval_2[0] ))
    union = max( interval_1[1], interval_2[1]) - min(interval_1[0], interval_2[0] )
    if abs(union) < 0.0000000001:
        return 1.0
    else:
        return intersection / float( union )


def to_dict_or_none( obj ):
    if obj is None:
        return None
    return obj.to_dict()

    
