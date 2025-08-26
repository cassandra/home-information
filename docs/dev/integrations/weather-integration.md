# Weather Integration

## Weather Data Source Architecture

The weather system uses a pluggable integration architecture designed to support multiple external weather APIs without dependencies on any single source.

### Auto-Discovery System

Weather data sources are automatically discovered by the system using a simple class-based pattern:

1. **Create Source File**: Add new Python file in `hi.apps.weather.weather_sources/`
2. **Implement Base Class**: Define subclass of `WeatherDataSource` 
3. **System Discovery**: Framework automatically finds and configures your source

### Implementation Steps

#### 1. Study the Base Class

Before implementing, review `WeatherDataSource` base class in `src/hi/apps/weather/weather_data_source.py` to understand:

- Required constructor parameters
- Available configuration methods (`requires_api_key()`, `get_default_enabled_state()`)
- Properties you can access (`self.api_key`, `self.is_enabled`, `self.geographic_location`)
- Abstract methods you must implement (`get_data()`)

#### 2. Study Existing Examples

Look at current implementations in `src/hi/apps/weather/weather_sources/` to see:

- How constructor parameters are set
- How configuration methods are overridden
- How `get_data()` is implemented
- Best practices for error handling and logging

#### 3. Create Your Implementation

Create your weather source file following the patterns observed in existing sources.

### Key Configuration Methods

Refer to the `WeatherDataSource` base class for exact method signatures:

- `requires_api_key()` - Return `True` if your source needs an API key
- `get_default_enabled_state()` - Return `False` if your source should be disabled by default
- `get_data()` - Your main implementation for fetching weather data

### Implementation Example

```python
# hi/apps/weather/weather_sources/my_weather_source.py
from hi.apps.weather.weather_data_source import WeatherDataSource
import requests

class MyWeatherSource(WeatherDataSource):
    def __init__(self):
        super().__init__(
            source_id='my_weather',
            label='My Weather Service',
            priority=100,
            rate_limit_seconds=300
        )
    
    def requires_api_key(self):
        return True
    
    def get_default_enabled_state(self):
        return False
    
    def get_data(self):
        """Fetch and return weather data in unified format"""
        if not self.is_enabled or not self.api_key:
            return None
            
        try:
            response = requests.get(
                f'https://api.myweather.com/current',
                params={'key': self.api_key, 'location': self.location},
                timeout=30
            )
            response.raise_for_status()
            
            # Transform API response to unified format
            return self.transform_to_unified_format(response.json())
            
        except Exception as e:
            self.logger.error(f"Failed to fetch weather data: {e}")
            return None
    
    def transform_to_unified_format(self, api_data):
        """Transform external API data to internal unified format"""
        # Map external data to hi.apps.weather.transient_models format
        pass
```

## Auto-Discovery Features

When you add a weather source file, the system automatically provides:

✅ **Auto-Discovery**: System finds your class at startup  
✅ **Settings Creation**: Creates enable/disable checkbox in config UI  
✅ **API Key Settings**: Creates API key input field (if `requires_api_key()` returns `True`)  
✅ **Priority Handling**: Respects priority ordering for data source selection  
✅ **Enable/Disable**: Only polls enabled sources  
✅ **Rate Limiting**: Enforces your specified rate limits  

## Configuration UI Integration

Once added, your weather source automatically appears in the system configuration under **Settings > Weather** with appropriate controls based on your implementation.

**Important**: Run Django migrations after adding new sources. Even if no new migrations exist, the discovery and automatic database settings creation is triggered by a post-migration signal.

## Data Integration Patterns

### Unified Data Format

Each weather source must map its external API data to the unified format defined in `hi.apps.weather.transient_models`. This ensures consistent data handling regardless of source.

### Caching Strategy

Each API module should cache data appropriately to reduce API calls:

- **Astronomical data**: Only needs fetching once per day
- **Historical weather data**: Usually never changes once fetched
- **Current conditions**: Cache based on API provider recommendations
- **Forecast data**: Balance between freshness and rate limits

### Error Handling

Implement robust error handling:

```python
def get_data(self):
    try:
        # API call implementation
        pass
    except requests.exceptions.Timeout:
        self.logger.warning("Weather API request timed out")
        return None
    except requests.exceptions.HTTPError as e:
        self.logger.error(f"Weather API HTTP error: {e}")
        return None
    except Exception as e:
        self.logger.exception(f"Unexpected error in weather data fetch: {e}")
        return None
```

## Priority and Data Resolution

The system uses priority ordering to resolve data from multiple sources:

- **Higher priority sources** take precedence for primary data
- **Lower priority sources** fill in missing data points
- **Lower priority sources** may overwrite data if existing data is stale
- **Rate limiting** prevents excessive API calls

## Testing Your Integration

1. **Restart Django server** to trigger auto-discovery
2. **Check logs** for discovery message confirming your source was found
3. **Verify settings** appear in config UI at Settings > Weather
4. **Test enable/disable** functionality
5. **Verify data fetching** and unified format transformation

## Best Practices

- **Study Existing Code**: Always examine current implementations in `weather_sources/` before starting
- **Unique IDs**: Use lowercase, no spaces for your source ID
- **Descriptive Labels**: Use proper human-readable names for UI display
- **Appropriate Priorities**: Check existing sources to choose suitable priority level
- **Rate Limits**: Respect API provider limits and document them
- **Error Handling**: Handle API failures gracefully following existing patterns
- **Logging**: Use appropriate log levels for debugging and monitoring
- **Data Validation**: Validate external API responses before transformation
- **Timeout Handling**: Always set reasonable timeouts for external API calls

## Troubleshooting

### Source Not Discovered
- Verify file is in correct directory: `hi.apps.weather.weather_sources/`
- Check class inherits from `WeatherDataSource`
- Restart Django server
- Check Django logs for error messages

### Settings Not Appearing
- Run `./manage.py migrate` to trigger post-migration signals
- Check database for weather source settings entries
- Verify configuration UI has been refreshed

### API Integration Issues
- Enable debug logging for detailed API interaction logs
- Test API endpoints independently
- Verify API key configuration and permissions
- Check rate limiting and quota usage

## Related Documentation
- Integration guidelines: [Integration Guidelines](integration-guidelines.md)
- External API standards: [External API Standards](external-api-standards.md)
- Weather business logic: [Domain Guidelines](../domain/domain-guidelines.md#weather-integration)
- Service patterns: [Service Patterns](service-patterns.md)