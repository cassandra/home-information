from django.core.management.base import BaseCommand


class Command( BaseCommand ):
    """
    Command provided so that we can automate creating groups we need
    for the game, mostly around tools and content management administrative
    functions.
    """
    def handle( self, *args, **options ):
        # TODO: Placeholder for eventual groups creation.
        return
    
