from django.contrib import admin

from . import models


class IntegrationPropertyInLine(admin.TabularInline):
    model = models.IntegrationProperty
    extra = 0
    show_change_link = True


@admin.register(models.Integration)
class IntegrationAdmin(admin.ModelAdmin):
    show_full_result_count = False
    
    list_display = (
        'integration_type_str',
        'is_enabled',
        'created_datetime',
        'updated_datetime',
    )

    inlines = [ IntegrationPropertyInLine, ]
