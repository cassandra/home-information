from django.db import models


class UnsubscribedEmailManager(models.Manager):

    def exists_by_user( self, user ):
        if not user.email:
            return False
        return self.exists_by_email( email = user.email )
    
    def exists_by_email( self, email : str ):
        if not email:
            return False
        return self.filter( email__iexact = email ).exists()

    
