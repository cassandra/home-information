"""Choice lists for the Open-Meteo simulator state editor.

Self-contained on purpose — the weather simulators do not import from
``hi.apps.weather`` (see ``payload_utils`` module docstring). The codes
are the WMO weather-interpretation codes Open-Meteo returns; the main
app maps them to descriptions on its side.
"""

# A useful subset of WMO codes spanning clear → severe. Operators who
# need a code not listed can extend this list.
WEATHER_CODE_CHOICES = [
    ( 0, '0 — Clear sky' ),
    ( 1, '1 — Mainly clear' ),
    ( 2, '2 — Partly cloudy' ),
    ( 3, '3 — Overcast' ),
    ( 45, '45 — Fog' ),
    ( 48, '48 — Depositing rime fog' ),
    ( 51, '51 — Light drizzle' ),
    ( 53, '53 — Moderate drizzle' ),
    ( 55, '55 — Dense drizzle' ),
    ( 61, '61 — Slight rain' ),
    ( 63, '63 — Moderate rain' ),
    ( 65, '65 — Heavy rain' ),
    ( 66, '66 — Light freezing rain' ),
    ( 71, '71 — Slight snow' ),
    ( 73, '73 — Moderate snow' ),
    ( 75, '75 — Heavy snow' ),
    ( 80, '80 — Slight rain showers' ),
    ( 81, '81 — Moderate rain showers' ),
    ( 82, '82 — Violent rain showers' ),
    ( 85, '85 — Slight snow showers' ),
    ( 95, '95 — Thunderstorm' ),
    ( 96, '96 — Thunderstorm with slight hail' ),
]
