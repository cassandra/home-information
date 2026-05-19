from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode

from . import forms
from .models import SimProfile
from .module_registry import find_module
from .profile_manager import ProfileManager


def _resolve_module( module_key : str ):
    module = find_module( module_key )
    if module is None:
        raise BadRequest( f'Unknown simulator module: {module_key!r}' )
    return module


class CreateProfileView( View ):

    MODAL_TEMPLATE_NAME = 'profile/modals/profile_create.html'

    def get(self, request, module_key, *args, **kwargs):
        module = _resolve_module( module_key )
        context = {
            'module': module,
            'sim_profile_form': forms.SimProfileForm(),
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post(self, request, module_key, *args, **kwargs):
        module = _resolve_module( module_key )
        form = forms.SimProfileForm( request.POST )
        if not form.is_valid():
            context = {
                'module': module,
                'sim_profile_form': form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )
        new_profile = ProfileManager().create(
            module_key = module_key,
            name = form.cleaned_data[ 'name' ],
        )
        ProfileManager().set_current( module_key, new_profile )
        return antinode.refresh_response()


class EditProfileView( View ):

    MODAL_TEMPLATE_NAME = 'profile/modals/profile_edit.html'

    def get(self, request, module_key, profile_id, *args, **kwargs):
        module = _resolve_module( module_key )
        profile = get_object_or_404( SimProfile, pk = profile_id,
                                     module_key = module_key )
        context = {
            'module': module,
            'sim_profile': profile,
            'sim_profile_form': forms.SimProfileForm( instance = profile ),
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post(self, request, module_key, profile_id, *args, **kwargs):
        module = _resolve_module( module_key )
        profile = get_object_or_404( SimProfile, pk = profile_id,
                                     module_key = module_key )
        form = forms.SimProfileForm( request.POST, instance = profile )
        if not form.is_valid():
            context = {
                'module': module,
                'sim_profile': profile,
                'sim_profile_form': form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )
        form.save()
        return antinode.refresh_response()


class CloneProfileView( View ):

    MODAL_TEMPLATE_NAME = 'profile/modals/profile_clone.html'

    def get(self, request, module_key, profile_id, *args, **kwargs):
        module = _resolve_module( module_key )
        source_profile = get_object_or_404( SimProfile, pk = profile_id,
                                            module_key = module_key )
        context = {
            'module': module,
            'source_profile': source_profile,
            'sim_profile_form': forms.SimProfileForm(
                initial = { 'name': self._suggest_name( source_profile ) },
            ),
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post(self, request, module_key, profile_id, *args, **kwargs):
        module = _resolve_module( module_key )
        source_profile = get_object_or_404( SimProfile, pk = profile_id,
                                            module_key = module_key )
        form = forms.SimProfileForm( request.POST )
        if not form.is_valid():
            context = {
                'module': module,
                'source_profile': source_profile,
                'sim_profile_form': form,
            }
            return render( request, self.MODAL_TEMPLATE_NAME, context )
        with transaction.atomic():
            new_profile = ProfileManager().clone(
                module_key = module_key,
                source_profile = source_profile,
                new_name = form.cleaned_data[ 'name' ],
            )
        ProfileManager().set_current( module_key, new_profile )
        return antinode.refresh_response()

    @staticmethod
    def _suggest_name( source_profile : SimProfile ) -> str:
        candidate = f'{source_profile.name} (copy)'
        if not SimProfile.objects.filter(
                module_key = source_profile.module_key,
                name = candidate ).exists():
            return candidate
        for index in range( 2, 100 ):
            candidate = f'{source_profile.name} (copy {index})'
            if not SimProfile.objects.filter(
                    module_key = source_profile.module_key,
                    name = candidate ).exists():
                return candidate
        return f'{source_profile.name} (copy)'


class DeleteProfileView( View ):

    MODAL_TEMPLATE_NAME = 'profile/modals/profile_delete.html'

    def get(self, request, module_key, profile_id, *args, **kwargs):
        module = _resolve_module( module_key )
        profile = get_object_or_404( SimProfile, pk = profile_id,
                                     module_key = module_key )
        context = {
            'module': module,
            'sim_profile': profile,
        }
        return render( request, self.MODAL_TEMPLATE_NAME, context )

    def post(self, request, module_key, profile_id, *args, **kwargs):
        _resolve_module( module_key )
        profile = get_object_or_404( SimProfile, pk = profile_id,
                                     module_key = module_key )
        ProfileManager().delete( module_key = module_key, profile = profile )
        return antinode.refresh_response()


class SwitchProfileView( View ):

    def get(self, request, module_key, profile_id, *args, **kwargs):
        _resolve_module( module_key )
        profile = get_object_or_404( SimProfile, pk = profile_id,
                                     module_key = module_key )
        ProfileManager().set_current( module_key = module_key, profile = profile )
        # Profile switching is always initiated from the tab being
        # switched, so reloading the page that issued the request lands
        # the user back on the same tab.
        referer = request.META.get( 'HTTP_REFERER' )
        return HttpResponseRedirect( referer or reverse( 'simulator_home' ))
