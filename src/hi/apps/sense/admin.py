from django.contrib import admin

from . import models


class SensorHistoryInLine(admin.TabularInline):
    model = models.SensorHistory
    extra = 0
    show_change_link = True

    
@admin.register(models.Sensor)
class SensorAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'name',
        'entity_state',
        'sensor_type_str',
        'integration_id',
        'integration_name',
        'persist_history',
    )

    search_fields = ['name']
    readonly_fields = ( 'entity_state', )
    inlines = [
        SensorHistoryInLine,
    ]

    
@admin.register(models.SensorHistory)
class SensorHistoryAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'sensor',
        'value',
        'response_datetime',
        'details',
        'has_video_stream',
        'correlation_role_str',
        'correlation_id',
        'source_image_url',
    )

    search_fields = ['sensor__name']
    readonly_fields = ( 'sensor', )
    ordering = ( '-response_datetime', )

