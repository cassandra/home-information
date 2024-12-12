from django.contrib import admin

from . import models


class SubsystemAttributeInLine(admin.TabularInline):
    model = models.SubsystemAttribute
    extra = 0
    show_change_link = True


@admin.register(models.Subsystem)
class SubsystemAdmin(admin.ModelAdmin):
    show_full_result_count = False
    
    list_display = (
        'name',
        'subsystem_key',
        'created_datetime',
    )

    inlines = [ SubsystemAttributeInLine, ]

