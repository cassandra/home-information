# Adding Weather Data Sources

This guide explains how to add new weather data sources to the Home Information system. The weather system uses auto-discovery, making it extremely simple to add new sources.

## Quick Start

To add a new weather source, you only need to:

1. Create a new Python file in `src/hi/apps/weather/weather_sources/`
2. Implement a class that inherits from `WeatherDataSource`
3. **That's it!** The system will automatically discover and configure your source

## Implementation Steps

### 1. Study the Base Class

Before implementing, review the `WeatherDataSource` base class in `src/hi/apps/weather/weather_data_source.py` to understand:

- Required constructor parameters
- Available configuration methods (`requires_api_key()`, `get_default_enabled_state()`)
- Properties you can access (`self.api_key`, `self.is_enabled`, `self.geographic_location`)
- Abstract methods you must implement (`get_data()`)

### 2. Study Existing Examples

Look at the current implementations in `src/hi/apps/weather/weather_sources/` to see:

- How constructor parameters are set
- How configuration methods are overridden
- How `get_data()` is implemented
- Best practices for error handling and logging

### 3. Create Your Implementation

Create your weather source file following the patterns you observed in the existing sources.

## Key Configuration Methods

Refer to the `WeatherDataSource` base class for the exact method signatures, but the key methods you may want to override are:

- `requires_api_key()` - Return `True` if your source needs an API key
- `get_default_enabled_state()` - Return `False` if your source should be disabled by default
- `get_data()` - Your main implementation for fetching weather data

## What Happens Automatically

When you add your weather source file:

✅ **Auto-Discovery**: System finds your class at startup  
✅ **Settings Creation**: Creates enable/disable checkbox in config UI  
✅ **API Key Settings**: Creates API key input field (if `requires_api_key()` returns `True`)  
✅ **Priority Handling**: Respects priority ordering for data source selection  
✅ **Enable/Disable**: Only polls enabled sources  
✅ **Rate Limiting**: Enforces your specified rate limits  

## Configuration UI

Once added, your weather source will automatically appear in the system configuration under **Settings > Weather** with appropriate controls based on your implementation.

## Testing Your Source

1. Restart the Django server
2. Check logs for discovery message confirming your source was found
3. Verify settings appear in config UI
4. Test enabling/disabling your source

## Best Practices

- **Study Existing Code**: Always look at current implementations in `weather_sources/` before starting
- **Unique IDs**: Use lowercase, no spaces for your source ID
- **Descriptive Labels**: Use proper human-readable names
- **Appropriate Priorities**: Check existing sources to choose a suitable priority level
- **Rate Limits**: Respect API provider limits
- **Error Handling**: Handle API failures gracefully following existing patterns
- **Logging**: Use appropriate log levels for debugging

## Finding Current Examples

To see what weather sources currently exist and how they're implemented, look in:
- `src/hi/apps/weather/weather_sources/` - All current implementations
- Weather configuration UI (Settings > Weather) - To see what sources are active

This ensures you're always working with the most current examples and patterns.