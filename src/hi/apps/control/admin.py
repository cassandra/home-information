from django.contrib import admin

from . import models


@admin.register(models.Controller)
class ControllerAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'name',
        'entity_state',
        'controller_type_str',
        'integration_id',
        'integration_name',
    )

    search_fields = ['name']
    readonly_fields = ( 'entity_state', )

    
@admin.register(models.ControllerHistory)
class ControllerHistoryAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'controller',
        'value',
        'created_datetime',
    )

    search_fields = ['controller__name']
    readonly_fields = ( 'controller', )
    ordering = ( '-created_datetime', )

