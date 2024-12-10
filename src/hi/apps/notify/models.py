from django.db import models

from . import managers


class UnsubscribedEmail( models.Model ):

    objects = managers.UnsubscribedEmailManager()
    
    email = models.EmailField(
        unique = True,
        max_length = 254,
        verbose_name = 'Email',
    )

    created_datetime = models.DateTimeField(
        'Created',
        auto_now_add = True,
        blank = True,
        db_index = True,
    )


