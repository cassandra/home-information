from dataclasses import dataclass

from django.http import HttpRequest


@dataclass
class SimViewParameters:

    simulator_id    : str       = None  # Last active simulator
    
    def __post_init__(self):
        return
    
    def to_session( self, request : HttpRequest ):
        if not hasattr( request, 'session' ):
            return
        request.session['simulator_id'] = self.simulator_id
        return

    @staticmethod
    def from_session( request : HttpRequest ):
        if not request:
            return SimViewParameters()
        if not hasattr( request, 'session' ):
            return SimViewParameters()
        try:
            simulator_id = int( request.session.get( 'simulator_id' ))
        except ( TypeError, ValueError ):
            simulator_id = None

        return SimViewParameters(
            simulator_id = simulator_id,
        )
    
