from urllib.parse import urlencode

from django.core.exceptions import BadRequest
from django.http import Http404
from django.urls import reverse

from hi.apps.entity.models import Entity, EntityState


class EntityViewMixin:

    def get_entity( self, request, *args, **kwargs ) -> Entity:
        """ Assumes there is a required entity_id in kwargs """
        try:
            entity_id = int( kwargs.get( 'entity_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid item id.' )
        try:
            return Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404( request )

    def redirect_home_w_geometry( self, request ):
        """Redirect to home, carrying the user's current pan/zoom (from the
        session) as query params, so an edit operation's full reload keeps
        the view where the user left it instead of snapping back to the
        LocationView's stored geometry. Scoped to the triggering operation:
        a bare home redirect when no geometry is tracked (e.g. acting from a
        collection view, or before any pan/zoom). The host view supplies
        ``redirect_response`` (HiModalView)."""
        redirect_url = reverse('home')
        svg_view_box = request.view_parameters.last_svg_view_box
        if svg_view_box is not None:
            params = { 'svg_view_box': str(svg_view_box) }
            svg_rotate = request.view_parameters.last_svg_rotate
            if svg_rotate is not None:
                params['svg_rotate'] = svg_rotate
            redirect_url = f'{redirect_url}?{urlencode(params)}'
        return self.redirect_response( request, redirect_url )


class EntityStateViewMixin:

    def get_entity_state( self, request, *args, **kwargs ) -> EntityState:
        """ Assumes there is a required entity_state_id in kwargs """
        try:
            entity_state_id = int( kwargs.get( 'entity_state_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid entity state id.' )
        try:
            return EntityState.objects.get( id = entity_state_id )
        except EntityState.DoesNotExist:
            raise Http404( request )
