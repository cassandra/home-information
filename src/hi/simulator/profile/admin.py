from django.contrib import admin

from .models import SimProfile


@admin.register( SimProfile )
class SimProfileAdmin( admin.ModelAdmin ):

    show_full_result_count = False

    list_display = (
        'module_key',
        'name',
        'last_switched_to_datetime',
        'created_datetime',
    )

    search_fields = [ 'module_key', 'name' ]
    readonly_fields = ( 'created_datetime', 'last_switched_to_datetime' )
    list_filter = ( 'module_key', )
