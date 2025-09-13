from django.shortcuts import render
from django.views.generic import View


class ProfileDevtoolsHomeView(View):

    def get(self, request, *args, **kwargs):
        context = {}
        return render(request, "profiles/tests/devtools/home.html", context)


class ProfileDevtoolsSnapshotView(View):

    def get(self, request, *args, **kwargs):
        pass
    
