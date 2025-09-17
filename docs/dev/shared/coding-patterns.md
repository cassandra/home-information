## Coding Patterns

- [ ] New modal dialogs extend one of the standard base classes in `hi/templates/modals`.
- [ ] New model dialogs extend the `HiModalView` class.
- [ ] The `antinode.js` framework and pattern is used for async/ajax content updates and modals.
- [ ] Javascript uses jQuery for DOM manipulations.
- [ ] Minimal business logic in templates: views prepare the template context needed
- [ ] Minimal business logic in Django views: use helepr classes
- [ ] No ORM calls in template tags
- [ ] Only internal system icons are used (no font-awesome icon).
- [ ] Appropriate icons are selected, or new icons created.




zzzzzzzz
# Django Patterns

## Model Design Patterns

### Abstract Base Models

Use abstract models for common functionality:

```python
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class Entity(IntegrationKeyMixin, TimestampedModel):
    name = models.CharField(max_length=100)
    # Inherits integration keys and timestamps
```

### Custom Model Managers

Create custom managers for common query patterns:

```python
class EntityManager(models.Manager):
    def active(self):
        """Get only active entities"""
        return self.filter(is_active=True)
    
    def with_sensors(self):
        """Get entities that have sensors"""
        return self.filter(sensors__isnull=False).distinct()
    
    def for_location_view(self, location_view):
        """Get entities visible in location view"""
        return self.filter(
            location=location_view.location,
            entityposition__isnull=False
        ).select_related('entity_type', 'location')

class Entity(models.Model):
    objects = EntityManager()
    # ... model fields ...
```

### Model Property Patterns

Use properties for computed fields and business logic:

```python
class Entity(models.Model):
    @property
    def has_recent_activity(self):
        """Check if entity had activity in last hour"""
        if not hasattr(self, '_recent_activity'):
            cutoff = timezone.now() - timedelta(hours=1)
            self._recent_activity = self.sensor_responses.filter(
                timestamp__gte=cutoff
            ).exists()
        return self._recent_activity
    
    @property
    def display_status(self):
        """Get human-readable status"""
        return self.get_current_state_display()
    
    def get_current_state_display(self):
        """Business logic for state display"""
        latest_response = self.get_latest_sensor_response()
        if not latest_response:
            return 'Unknown'
        return latest_response.get_display_value()
```

### Model Method Patterns

Encapsulate business logic in model methods:

```python
class Alert(models.Model):
    def get_first_visual_content(self):
        """Get first image or visual content for display"""
        for alarm in self.alarm_list:
            for source_detail in alarm.source_details_list:
                if source_detail.image_url:
                    return {
                        'type': 'image',
                        'url': source_detail.image_url,
                        'description': source_detail.description
                    }
        return None
    
    def get_priority_level(self):
        """Calculate priority based on alarm levels"""
        if not self.alarm_list:
            return 'low'
        
        max_level = max(alarm.level for alarm in self.alarm_list)
        if max_level >= AlarmLevel.CRITICAL:
            return 'critical'
        elif max_level >= AlarmLevel.WARNING:
            return 'high'
        return 'medium'
```

## View Patterns

### Class-Based View Mixins

Create reusable mixins for common view functionality:

```python
class LocationViewContextMixin:
    """Add location view context to all views"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_location_view'] = self.get_current_location_view()
        context['available_location_views'] = LocationView.objects.all()
        return context
    
    def get_current_location_view(self):
        """Get location view from session or default"""
        location_view_id = self.request.session.get('location_view_id')
        if location_view_id:
            try:
                return LocationView.objects.get(id=location_view_id)
            except LocationView.DoesNotExist:
                pass
        return LocationView.objects.filter(is_default=True).first()

class EntityListView(LocationViewContextMixin, ListView):
    model = Entity
    template_name = 'entity/pages/entity_list.html'
    
    def get_queryset(self):
        location_view = self.get_current_location_view()
        if location_view:
            return Entity.objects.for_location_view(location_view)
        return Entity.objects.active()
```

### Form Processing Patterns

Standard form handling with proper error handling:

```python
class EntityUpdateView(UpdateView):
    model = Entity
    form_class = EntityForm
    template_name = 'entity/pages/entity_edit.html'
    
    def form_valid(self, form):
        """Handle successful form submission"""
        try:
            # Perform any additional business logic
            entity = form.save(commit=False)
            entity.updated_by = self.request.user
            entity.save()
            
            # Add success message
            messages.success(
                self.request,
                f"Entity '{entity.name}' updated successfully."
            )
            
            return super().form_valid(form)
            
        except ValidationError as e:
            form.add_error(None, e.message)
            return self.form_invalid(form)
        except Exception as e:
            form.add_error(None, "An unexpected error occurred.")
            logger.exception(f"Error updating entity {entity.id}: {e}")
            return self.form_invalid(form)
    
    def get_success_url(self):
        """Redirect based on user action"""
        if 'save_and_continue' in self.request.POST:
            return reverse('entity_edit', kwargs={'pk': self.object.pk})
        return reverse('entity_list')
```

### AJAX View Patterns

Handle both regular and AJAX requests:

```python
class EntityActionView(View):
    def post(self, request, *args, **kwargs):
        entity = get_object_or_404(Entity, id=kwargs['entity_id'])
        action = request.POST.get('action')
        
        try:
            result = self.perform_action(entity, action)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f"Action '{action}' completed successfully",
                    'result': result,
                    'entity_id': entity.id
                })
            else:
                messages.success(request, f"Action '{action}' completed successfully")
                return redirect('entity_detail', pk=entity.id)
                
        except Exception as e:
            error_msg = f"Failed to perform action '{action}': {str(e)}"
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg
                }, status=400)
            else:
                messages.error(request, error_msg)
                return redirect('entity_detail', pk=entity.id)
    
    def perform_action(self, entity, action):
        """Override in subclasses for specific actions"""
        raise NotImplementedError("Subclasses must implement perform_action")
```

## Custom Template Tags and Filters

### Inclusion Tags for Reusable Components

```python
# In templatetags/entity_tags.py
from django import template
from django.template.loader import render_to_string

register = template.Library()

@register.inclusion_tag('entity/tags/entity_status_badge.html')
def entity_status_badge(entity, size='normal'):
    """Render entity status badge with appropriate styling"""
    status = entity.get_current_status()
    css_class = f'badge-{status.get_css_class()}'
    
    return {
        'entity': entity,
        'status': status,
        'css_class': css_class,
        'size': size,
    }

@register.simple_tag
def entity_action_url(entity, action):
    """Generate URL for entity actions"""
    return reverse('entity_action', kwargs={
        'entity_id': entity.id,
        'action': action
    })
```

### Custom Filters

```python
@register.filter
def time_since_activity(entity):
    """Get human-readable time since last activity"""
    latest_response = entity.get_latest_sensor_response()
    if not latest_response:
        return "Never"
    
    return timesince(latest_response.timestamp)

@register.filter
def status_css_class(entity_state):
    """Get CSS class for entity state"""
    # For complete status display implementation including CSS classes,
    # colors, and visual progression, see [Entity Status Display](../frontend/entity-status-display.md)
    status_map = {
        'active': 'status-active',
        'recent': 'status-recent',
        'past': 'status-past',
        'idle': 'status-idle',
        'unknown': 'status-unknown',
    }
    return status_map.get(entity_state.lower(), 'status-unknown')
```

## Django Admin Customization

### Custom Admin Classes

```python
# In admin.py
@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ['name', 'entity_type', 'location', 'is_active', 'last_updated']
    list_filter = ['entity_type', 'location', 'is_active', 'created_at']
    search_fields = ['name', 'integration_id']
    readonly_fields = ['created_at', 'updated_at', 'integration_key']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'entity_type', 'location', 'is_active')
        }),
        ('Integration', {
            'fields': ('integration_name', 'integration_id', 'integration_key'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries for admin list view"""
        return super().get_queryset(request).select_related(
            'entity_type', 'location'
        )
    
    def last_updated(self, obj):
        """Custom column for last update time"""
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    last_updated.short_description = 'Last Updated'
    last_updated.admin_order_field = 'updated_at'
```

## Signal Patterns

### Model Signals for Business Logic

```python
# In models.py or signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

@receiver(post_save, sender=Entity)
def entity_post_save(sender, instance, created, **kwargs):
    """Handle entity creation/update"""
    if created:
        # Initialize default entity states
        for state_type in EntityStateType.get_defaults_for_entity_type(instance.entity_type):
            EntityState.objects.get_or_create(
                entity=instance,
                entity_state_type=state_type,
                defaults={'current_value': state_type.default_value}
            )
    
    # Update search index or cache
    search_index.update_entity(instance)
    cache.delete(f'entity:{instance.id}')

@receiver(pre_delete, sender=EntityImage)
def cleanup_entity_image(sender, instance, **kwargs):
    """Clean up image files before deleting model"""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
```

## Migration Patterns

### Data Migrations

```python
# In migration file
from django.db import migrations

def populate_entity_states(apps, schema_editor):
    """Populate entity states for existing entities"""
    Entity = apps.get_model('entity', 'Entity')
    EntityState = apps.get_model('entity', 'EntityState')
    EntityStateType = apps.get_model('entity', 'EntityStateType')
    
    default_state_type = EntityStateType.objects.get(name='status')
    
    for entity in Entity.objects.filter(states__isnull=True):
        EntityState.objects.create(
            entity=entity,
            entity_state_type=default_state_type,
            current_value='unknown'
        )

def reverse_populate_entity_states(apps, schema_editor):
    """Reverse migration - remove populated states"""
    EntityState = apps.get_model('entity', 'EntityState')
    EntityState.objects.filter(current_value='unknown').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('entity', '0005_add_entity_state_model'),
    ]
    
    operations = [
        migrations.RunPython(
            populate_entity_states,
            reverse_populate_entity_states
        ),
    ]
```

### Schema Migrations with Indexes

```python
class Migration(migrations.Migration):
    atomic = False  # For PostgreSQL index creation
    
    operations = [
        migrations.AddIndex(
            model_name='sensorresponse',
            index=models.Index(
                fields=['sensor', '-timestamp'],
                name='sensor_response_sensor_time_idx'
            ),
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS entity_integration_key_idx ON entity_entity (integration_name, integration_id);",
            reverse_sql="DROP INDEX IF EXISTS entity_integration_key_idx;"
        ),
    ]
```

## Related Documentation
- Backend guidelines: [Backend Guidelines](backend-guidelines.md)
- Database conventions: [Database Conventions](database-conventions.md)
- Testing patterns: [Testing Patterns](../testing/testing-patterns.md)
- Performance optimization: [Architecture Overview](../shared/architecture-overview.md)
