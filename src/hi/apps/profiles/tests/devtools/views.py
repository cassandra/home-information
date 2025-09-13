import logging

from django.shortcuts import render
from django.views.generic import View

from hi.hi_async_view import HiModalView
from hi.views import bad_request_response
import hi.apps.common.antinode as antinode

from ...enums import ProfileType
from .profile_snapshot_generator import ProfileSnapshotGenerator

logger = logging.getLogger(__name__)


class ProfileDevtoolsHomeView(View):

    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, "profiles/tests/devtools/home.html", context)


class ProfileDevtoolsSnapshotView(HiModalView):

    def get_template_name(self) -> str:
        return 'profiles/tests/devtools/modals/snapshot_select.html'

    def get(self, request, *args, **kwargs):
        context = {
            'profile_types': ProfileType.choices(),
        }
        return self.modal_response(request, context)
    
    def post(self, request, *args, **kwargs):
        profile_type_name = request.POST.get('profile_type')
        output_to_tmp = request.POST.get('output_to_tmp', 'true') == 'true'
        
        if not profile_type_name:
            return bad_request_response(request, "Profile type is required")
        
        try:
            profile_type = ProfileType.from_name(profile_type_name)
        except ValueError:
            return bad_request_response(request, f"Invalid profile type: {profile_type_name}")
        
        try:
            generator = ProfileSnapshotGenerator()
            output_path = generator.generate_snapshot(profile_type, output_to_tmp)
            
            context = {
                'profile_type_label': profile_type.label,
                'output_path': str(output_path),
                'output_to_tmp': output_to_tmp,
            }
            
            return antinode.modal_from_template(
                request=request,
                template_name='profiles/tests/devtools/modals/snapshot_success.html',
                context=context
            )
            
        except ValueError as e:
            return bad_request_response(request, str(e))
        except Exception as e:
            logger.error(f"Failed to generate snapshot: {e}")
            return bad_request_response(request, "Failed to generate snapshot")
    
