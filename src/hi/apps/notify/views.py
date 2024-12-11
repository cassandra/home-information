import logging

from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.views.generic import View

from hi.apps.common.utils import hash_with_seed

from .models import UnsubscribedEmail

logger = logging.getLogger(__name__)


class EmailUnsubscribeView( View ):

    SUCCESS_PAGE_TEMPLATE_NAME = 'notify/pages/email_unsubscribe_success.html'
    
    def get( self, request, *args, **kwargs ):
        email = kwargs.get('email')
        token = kwargs.get('token')
        if not email or not token:
            raise BadRequest( 'Improperly formed unsubscribe url.' )
        
        # A psuedo-secure hash to prevent malicious unsubscribes.
        # Attackers needs to know a "seed" to be able to hash the email
        # properly. Motivation is that we should not require a user to
        # login or do any other complicated flow to be able to unsubscribe.
        #
        expected_token = hash_with_seed( email )
        context = { 'email': email }
        
        if expected_token != token:
            raise BadRequest( 'Invalid unsubscribe url.' )

        # If already unsubscribed, just treat like success.
        try:
            UnsubscribedEmail.objects.get( email__iexact = email )
            return render( request, self.SUCCESS_PAGE_TEMPLATE_NAME, context )
        except UnsubscribedEmail.DoesNotExist:
            pass

        try:
            UnsubscribedEmail.objects.create( email = email )
        except Exception as e:
            logger.exception( f'Problem unsubscribing email {email}', e )
        
        return render( request, self.SUCCESS_PAGE_TEMPLATE_NAME, context )
