from django.contrib import admin

from . import models


@admin.register(models.Sensor)
class SensorAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'name',
        'entity_state',
        'sensor_type_str',
        'integration_type_str',
        'integration_id',
    )

    search_fields = ['name']
    readonly_fields = ( 'entity_state', )

    
@admin.register(models.SensedEntity)
class SensedEntityAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'sensor',
        'entity',
        'created_datetime',
    )

    search_fields = ['sensor__name']
    readonly_fields = ( 'sensor', 'entity', )
    ordering = ( '-created_datetime', )

    
@admin.register(models.SensorHistory)
class SensorHistoryAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'sensor',
        'value',
        'created_datetime',
    )

    search_fields = ['sensor__name']
    readonly_fields = ( 'sensor', )
    ordering = ( '-created_datetime', )

