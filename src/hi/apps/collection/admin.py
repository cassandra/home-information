from django.contrib import admin

from .models import Collection, CollectionRelation


class CollectionRelationInline(admin.TabularInline):
    model = CollectionRelation
    extra = 1  # Number of empty forms to display in the inline

    
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    inlines = [ CollectionRelationInline ]
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)
