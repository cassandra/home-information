<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Weather

## Design Principles

- We do not want to depend on any one data source.
- We want to be able to merge data from multiple sources.

## Design Concetps

- We define our own "unified" view of weather data in `hi.apps.weather.transient_models`.
- We will populate that with data from various (API) sources (background tasks).
- Every data point will be associated with its source and the time in which it was fetched.
- Sources will have a priority ordering.
- Lower priority sources will predominatly be used for filling in missing data.
- Lower priority sources may overwrite existing data if the data is very stale.
- We need to respect rate and usage limits and cache weather data.

## Adding New Weather Data Source

Weather data sources are auto-discovered by ensuring you create a specific
subclass and put it in a specific directory.

- Create a new python file in `hi.apps.weather.weather_sources`.
- In that file, define a subclass of `WeatherDataSource`.
- You must provide an implementation for the following methods:
  - `get_data()`
  
- You may override the following methods:
  - zzz
  

The type of data each API might have can vary a lot, so the module is responsible for mapping the required API call(s) into the unified model used by the `WeatherManager`.  Further, each module should cache data if needed to reduce the number of API calls.  e.g.,
- Fetching the days atronommical data only needs to be done once day.
- Historical weather data is (usually) never going to change).
