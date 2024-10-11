from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone



class DatabaseLock(models.Model):

    name = models.CharField(
        max_length = 64,
        unique = True,
    )
    acquired_at = models.DateTimeField(
    )
    initialized = models.BooleanField(
        default = False,
    )

    class Meta:
        verbose_name = 'Database Lock'
        verbose_name_plural = 'Database Locks'

    def is_expired( self, timeout_seconds = 300 ):
        return timezone.now() > self.acquired_at + timedelta( seconds = timeout_seconds )

    @classmethod
    def acquire( cls,
                 name                : str,
                 timeout_seconds     : int   = 300,
                 for_initialization  : bool  = False ):
        
        with transaction.atomic():
            lock, created = DatabaseLock.objects.get_or_create(
                name = name,
                defaults = {
                    'acquired_at': timezone.now(),
                    'initialized': False,
                }
            )

            if created:
                return lock
            
            if lock.is_expired( timeout_seconds ):
                lock.acquired_at = timezone.now()
                lock.initialized = False
                lock.save()
                return lock
            
            if for_initialization and lock.initialized:
                return None

            return lock

    def release(self):
        self.delete()
        return

    def mark_initialized(self):
        self.initialized = True
        self.save()
        return
