from django.core.management.base import BaseCommand

from django.contrib.auth.models import Group


class Command(BaseCommand):
    """
    Command provided so that we can automate creating groups we need
    for the game, mostly around tools and content management administrative
    functions.
    """
    def handle(self, *args, **options):
        # TODO: Placeholder for eventual groups creation.
        return
    
