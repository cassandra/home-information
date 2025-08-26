# Service Patterns

## Home Assistant Integration

Full two-way sync with Home Assistant including:
- Entity mapping and state synchronization  
- Controller integration for device control
- Real-time event handling

```python
class HomeAssistantGateway(IntegrationGateway):
    def sync_entities(self):
        # Fetch entities from Home Assistant API
        # Map to local Entity models
        # Synchronize states and capabilities
        pass
```

## ZoneMinder Integration  

Camera and video surveillance system integration:
- Security monitoring and alerts
- Video stream management  
- Motion detection events

## Integration Patterns

- **HTTP API Clients**: REST API integration patterns
- **WebSocket Connections**: Real-time event handling  
- **Polling Services**: Periodic data synchronization
- **Webhook Handlers**: External system notifications

## Related Documentation
- Integration guidelines: [Integration Guidelines](integration-guidelines.md)
- Architecture overview: [Architecture Overview](../shared/architecture-overview.md)