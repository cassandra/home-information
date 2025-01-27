import logging
import uuid

from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from . import managers

logger = logging.getLogger(__name__)


class CustomUser( AbstractBaseUser, PermissionsMixin ):
    """Mostly a copy of Django's AbstractUser code, but with uuid and email as
    unique fields and without the username field.

    Adds additional states of user authentication beyond Django's Anonymous
    and Autheticated. New states:

        Anonymous - Same as normal Django AnonymousUser with no database entry.
        User, No Email - Authenticated but no email to enables app functionality before an email.
        User, Has Email - Authenticated and has set an email, but we have not verified they own that email.
        User, Has Verified Email - Authenticated, has set an email and we have verified they own that email.

    The UUID field allows us to have a unique, unchanging field for external references to users.
    """
    # For external referencing
    uuid = models.UUIDField(
        'UUID',
        default = uuid.uuid4,
        unique = True,
        null = False,
    )
    # All users without emails
    email = models.EmailField(
        _('email address'),
        unique = True,
        null = True,
        blank = True,
    )
    email_verified = models.BooleanField(
        _('email verified'),
        default = False,
        help_text = _('Has this email been verified.')
    )
    first_name = models.CharField(
        _('first name'),
        max_length = 150,
        blank = True
    )
    last_name = models.CharField(
        _('last name'),
        max_length = 150,
        blank = True
    )
    is_staff = models.BooleanField(
        _('staff status'),
        default = False,
        help_text = _('Designates whether the user can log into this admin site.')
    )
    is_active = models.BooleanField(
        _('active'),
        default = True,
        help_text = _('Designates whether this user should be treated as '
                      'active. Unselect this instead of deleting accounts.')
    )
    date_joined = models.DateTimeField(
        _('date joined'),
        default = timezone.now
    )

    objects = managers.CustomUserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = [ ]

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        if self.email:
            return self.email
        return self.uuid_str
    
    def clean(self):
        super().clean()
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email)
        return
    
    @property
    def uuid_str(self):
        return str(self.uuid)

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        raise NotImplementedError( f'Use different mechansism to email the user: {self}' )

    @property
    def admin_name(self):
        if self.email:
            return self.email
        if self.first_name:
            return self.first_name
        return self.uuid_str
   
