# Gateway Implementation

## Gateway Interface

All integrations implement the `IntegrationGateway` interface:

```python
class IntegrationGateway:
    def activate(self, integration_instance):
        """Handle integration activation"""
        raise NotImplementedError
    
    def deactivate(self, integration_instance):  
        """Handle integration deactivation"""
        raise NotImplementedError
        
    def manage(self, request, integration_instance):
        """Handle management interface"""
        raise NotImplementedError
```

## Configuration Management

Integration attributes are defined using enums:

```python
class MyIntegrationAttributes(IntegrationAttributeType):
    BASE_URL = ("base_url", str, "Base URL for API")
    API_KEY = ("api_key", str, "API authentication key")
    POLLING_INTERVAL = ("polling_interval", int, "Polling interval in seconds")
```

## URL Patterns

Management URLs use consistent patterns:

```python
# Integration management URL
{% url 'integration_manage' name=integration.integration_type.name %}
```

## Related Documentation  
- Integration guidelines: [Integration Guidelines](integration-guidelines.md)
- Service patterns: [Service Patterns](service-patterns.md)