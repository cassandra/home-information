# Database Conventions

### Indexing Strategy
```python
class Meta:
    indexes = [
        models.Index(fields=['integration_name', 'integration_id']),
        models.Index(fields=['timestamp']),
        models.Index(fields=['entity', '-timestamp']),
    ]
    db_table = 'entity_sensor_response'
```


## Related Documentation
- Backend guidelines: [Backend Guidelines](backend-guidelines.md)
- Coding patterns: [Django Patterns](../shared/coding-patterns.md)
