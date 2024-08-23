from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone


class DatabaseLock(models.Model):

    name = models.CharField(
        max_length = 64,
        unique = True
    )
    acquired_at = models.DateTimeField()

    def is_expired( self, timeout_seconds = 300 ):
        return timezone.now() > self.acquired_at + timedelta( seconds = timeout_seconds )

    def acquire( self, timeout_seconds = 300 ):
        """
        Attempt to acquire the lock. Returns True if the lock is acquired, False otherwise.
        """
        with transaction.atomic():
            lock, created = DatabaseLock.objects.get_or_create(
                name = self.name,
                defaults={ "acquired_at": timezone.now() }
            )
            if not created and not lock.is_expired( timeout_seconds ):
                return False

            lock.acquired_at = timezone.now()
            lock.save()
        return True

    def release(self):
        self.delete()
        return
