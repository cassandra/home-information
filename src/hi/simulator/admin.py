from django.contrib import admin

from . import models


@admin.register(models.DbSimEntity)
class DbSimEntityAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'sim_profile',
        'simulator_id',
        'entity_class_name',
        'entity_type_str',
        'editable_fields',
        'updated_datetime',
        'created_datetime',
    )

    search_fields = ['entity_class_name']
    readonly_fields = ( 'updated_datetime', 'created_datetime', )

    
@admin.register(models.SimProfile)
class SimProfileAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'name',
        'last_switched_to_datetime',
        'created_datetime',
    )

    search_fields = ['name']
    readonly_fields = ( 'created_datetime', 'last_switched_to_datetime', )
    
