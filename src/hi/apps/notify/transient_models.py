from dataclasses import dataclass, field
from typing import Dict, List, Union

from django.http.request import HttpRequest


@dataclass
class EmailData:
    """
    Input data format for sending emails with EmailSender. Caller defines
    the three required templates for formatting the email. The email sender
    will create a template context that includes the following variables
    that should be used in the email:

        BASE_URL  - Use this to forms any needed site links.
        HOME_URL - Url to the site's main landing page page.
        UNSUBSCRIBE_URL - Include as best practice if you send email more broadly.

    The templates are best defined by extending some pre-defined base
    templates to make all emails have a consistent formatting. e.g.,
    Unsubscribe URL appearing in footer.
    """

    # Set the request to None for background tasks, but also make sure
    # settings.BASE_URL_FOR_EMAIL_LINKS is set.
    #
    request                     : HttpRequest
    
    subject_template_name       : str
    message_text_template_name  : str
    message_html_template_name  : str
    to_email_address            : Union[ str, List[ str ]]

    # Defaults to system-wide settings.DEFAULT_FROM_EMAIL
    from_email_address          : str             = None
    
    template_context            : Dict[str, str]  = field( default_factory = dict )
    files                       : List            = None  # For attachments
    non_blocking                : bool            = True
                  
    # For testing (can use the unsubscribe link to test for the original intended "to" email)
    override_to_email_address   : str             = None
    
    
@dataclass
class NotificationItem:
    signature   : str
    title       : str
    

@dataclass
class Notification:
    title       : str
    item_list   : List[ NotificationItem ]
