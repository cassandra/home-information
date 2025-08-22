# URLs no longer needed here - views moved to concrete app implementations

# No longer needed - attribute history views are now implemented
# in each app with their concrete attribute models:
# - Entity app: entity_attribute_history, entity_attribute_restore
# - Location app: location_attribute_history, location_attribute_restore  
# - Config app: subsystem_attribute_history, subsystem_attribute_restore
# - Integrations app: integration_attribute_history, integration_attribute_restore

urlpatterns = [
    # No URLs needed here - abstract base views are used by concrete implementations
]
