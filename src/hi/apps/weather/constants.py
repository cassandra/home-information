class WeatherConstants:

    WEATHER_OVERVIEW_TEMPLATE_NAME = 'weather/panes/weather_overview.html'

    # Threshold beyond which the displayed current-conditions reading is
    # considered "stale" — drives a timestamp tint in the pane plus the
    # promotion of monitor-health messages from advisory to displayed.
    CONDITIONS_STALE_THRESHOLD_SECS = 60 * 60
