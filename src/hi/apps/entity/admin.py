from django.contrib import admin

from hi.apps.control.models import Controller
from hi.apps.sense.models import Sensor

from . import models


class EntityAttributeInLine(admin.TabularInline):
    model = models.EntityAttribute
    extra = 0
    show_change_link = True


class EntityAttributeHistoryInLine(admin.TabularInline):
    model = models.EntityAttributeHistory
    extra = 0
    show_change_link = True
    readonly_fields = ('value', 'changed_datetime')
    can_delete = False

    
class StateInLine(admin.TabularInline):
    model = models.EntityState
    extra = 0
    show_change_link = True

    
class PositionInLine(admin.TabularInline):
    model = models.EntityPosition
    extra = 0
    show_change_link = True

    
class PathInLine(admin.TabularInline):
    model = models.EntityPath
    extra = 0
    show_change_link = True

    
class ControllerInLine(admin.TabularInline):
    model = Controller
    extra = 0
    show_change_link = True

    
class SensorInLine(admin.TabularInline):
    model = Sensor
    extra = 0
    show_change_link = True

    
class EntityStateDelegationInLine(admin.TabularInline):
    model = models.EntityStateDelegation
    extra = 0
    show_change_link = True


class EntityViewInLine(admin.TabularInline):
    model = models.EntityView
    extra = 0
    show_change_link = True


@admin.register(models.Entity)
class EntityAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'name',
        'entity_type_str',
        'integration_id',
        'integration_name',
        'created_datetime',
    )

    search_fields = ['name']

    inlines = [
        EntityAttributeInLine,
        StateInLine,
        EntityViewInLine,
        PositionInLine,
        PathInLine,
        EntityStateDelegationInLine,
    ]
    

@admin.register(models.EntityState)
class EntityStateAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'entity',
        'name',
        'entity_state_type_str',
        'value_range_str',
        'units',
        'created_datetime',
    )

    search_fields = ['name']
    readonly_fields = ( 'entity', 'created_datetime', )
    inlines = [
        ControllerInLine,
        SensorInLine,
    ]

    
@admin.register(models.EntityStateDelegation)
class EntityStateDelegationAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'entity_state',
        'delegate_entity',
        'created_datetime',
    )

    search_fields = ['entity__name']
    readonly_fields = ( 'entity_state', 'delegate_entity', )


@admin.register(models.EntityAttribute)
class EntityAttributeAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'entity',
        'name',
        'value',
        'value_type_str',
        'attribute_type_str',
        'created_datetime',
    )

    search_fields = ['name', 'entity__name']
    readonly_fields = ('entity', 'created_datetime')
    inlines = [EntityAttributeHistoryInLine]
    
