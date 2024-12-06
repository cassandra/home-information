from django.contrib import admin

from . import models


class EventClauseInLine(admin.TabularInline):
    model = models.EventClause
    extra = 0
    show_change_link = True


class AlarmActionInLine(admin.TabularInline):
    model = models.AlarmAction
    extra = 0
    show_change_link = True


class ControlActionInLine(admin.TabularInline):
    model = models.ControlAction
    extra = 0
    show_change_link = True

    
@admin.register(models.EventDefinition)
class EventDefinitionAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'name',
        'event_window_secs',
        'dedupe_window_secs',
        'enabled',
    )

    search_fields = ['zzz']
    readonly_fields = ( 'created_datetime', 'updated_datetime', )
    inlines = [
        EventClauseInLine,
        AlarmActionInLine,
        ControlActionInLine,
    ]

    
@admin.register(models.EventHistory)
class EventHistoryAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'event_definition',
        'event_datetime',
    )

    search_fields = ['event_definition__name']
    readonly_fields = ( 'event_datetime', )
    
