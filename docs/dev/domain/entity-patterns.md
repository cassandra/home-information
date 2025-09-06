# Entity Patterns

## Entity-State Relationships

Entities have zero or more EntityState variables representing hidden state that can be sensed or controlled.

## Entity Positioning

Entities can be positioned in locations as icons or paths:
- **EntityPosition**: Icon-based representation with position, scale, rotation
- **EntityPath**: SVG path representation for areas or complex shapes

## Entity Delegation

EntityStateDelegation allows one entity's state to proxy another's:
- Delegate entity reflects principal entity's state
- Used for visual representation (e.g., thermometer shows room temperature)
- Supports one-to-one, one-to-many, many-to-one relationships

## Adding New Entity Types

To add a new entity type to the system:

### 1. Add Enum Entry

Add new entry in this enum:
```python
# hi.apps.entity.enums.EntityType
```

Add the new type to the appropriate group:
```python
# hi.apps.entity.enums.EntityGroupType  
```

### 2. Configure Visual Representation

Entity types can be displayed as icons or paths. For visual configuration details including SVG icon creation, styling, and template setup, see [Entity Visual Configuration](../frontend/entity-visual-configuration.md).

### 3. Simulator Support (Optional)

If the new type should be supported by the simulator, add it to:
```python
# hi.simulator.enums.SimEntityType
```

## Related Documentation
- Domain guidelines: [Domain Guidelines](domain-guidelines.md)
- Data model concepts: [Data Model](../shared/data-model.md)