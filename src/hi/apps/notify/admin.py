from django.contrib import admin

from . import models


@admin.register(models.UnsubscribedEmail)
class UnsubscribedEmailAdmin(admin.ModelAdmin):

    show_full_result_count = False
    
    list_display = (
        'email',
        'created_datetime',
    )

    search_fields = ['email']
