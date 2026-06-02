"""Choice lists for the NWS simulator alert editor.

Values match the NWS / CAP spec strings that ``NwsConverters`` parses
in the main app (lowercased before lookup). Keeping these here as plain
tuples instead of pulling from ``hi.apps.weather.enums`` avoids
coupling the simulator app to main-app imports at module load time.
"""

SEVERITY_CHOICES = [
    ( 'Extreme', 'Extreme' ),
    ( 'Severe', 'Severe' ),
    ( 'Moderate', 'Moderate' ),
    ( 'Minor', 'Minor' ),
    ( 'Unknown', 'Unknown' ),
]

CERTAINTY_CHOICES = [
    ( 'Observed', 'Observed' ),
    ( 'Likely', 'Likely' ),
    ( 'Possible', 'Possible' ),
    ( 'Unlikely', 'Unlikely' ),
    ( 'Unknown', 'Unknown' ),
]

URGENCY_CHOICES = [
    ( 'Immediate', 'Immediate' ),
    ( 'Expected', 'Expected' ),
    ( 'Future', 'Future' ),
    ( 'Unknown', 'Unknown' ),
]

STATUS_CHOICES = [
    ( 'Actual', 'Actual' ),
    ( 'Exercise', 'Exercise' ),
    ( 'System', 'System' ),
    ( 'Test', 'Test' ),
    ( 'Draft', 'Draft' ),
]

# NWS 'category' field — short codes that the main-app converter
# lowercases for lookup.
CATEGORY_CHOICES = [
    ( 'met', 'Meteorological' ),
    ( 'geo', 'Geological' ),
    ( 'safety', 'Public Safety' ),
    ( 'security', 'Security' ),
    ( 'rescue', 'Rescue' ),
    ( 'fire', 'Fire' ),
    ( 'health', 'Health' ),
    ( 'env', 'Environmental' ),
    ( 'transport', 'Transportation' ),
    ( 'infra', 'Infrastructure' ),
    ( 'other', 'Other' ),
]

# Subset of NWS three-letter event codes useful for exercising the
# main-app code-to-event-type mapping. Not exhaustive; operator can
# type the freeform event name to cover anything not listed.
EVENT_CODE_CHOICES = [
    ( '', '— None —' ),
    ( 'TOR', 'TOR — Tornado Warning' ),
    ( 'TOA', 'TOA — Tornado Watch' ),
    ( 'SVR', 'SVR — Severe Thunderstorm Warning' ),
    ( 'SVA', 'SVA — Severe Thunderstorm Watch' ),
    ( 'FFW', 'FFW — Flash Flood Warning' ),
    ( 'FFA', 'FFA — Flash Flood Watch' ),
    ( 'FLW', 'FLW — Flood Warning' ),
    ( 'FLA', 'FLA — Flood Watch' ),
    ( 'EWW', 'EWW — Extreme Wind Warning' ),
    ( 'HWW', 'HWW — High Wind Warning' ),
    ( 'BZW', 'BZW — Blizzard Warning' ),
    ( 'WSW', 'WSW — Winter Storm Warning' ),
    ( 'WSA', 'WSA — Winter Storm Watch' ),
    ( 'HUW', 'HUW — Hurricane Warning' ),
    ( 'HUA', 'HUA — Hurricane Watch' ),
    ( 'TRW', 'TRW — Tropical Storm Warning' ),
    ( 'TRA', 'TRA — Tropical Storm Watch' ),
    ( 'TSW', 'TSW — Tsunami Warning' ),
    ( 'TSA', 'TSA — Tsunami Watch' ),
    ( 'FRW', 'FRW — Fire Warning' ),
    ( 'RFW', 'RFW — Red Flag Warning' ),
    ( 'AFW', 'AFW — Ashfall Warning' ),
    ( 'EQW', 'EQW — Earthquake Warning' ),
    ( 'AQA', 'AQA — Air Quality Alert' ),
    ( 'CDW', 'CDW — Civil Danger Warning' ),
    ( 'CEM', 'CEM — Civil Emergency Message' ),
    ( 'LAE', 'LAE — Local Area Emergency' ),
    ( 'TST', 'TST — Test Message' ),
]

# METAR sky-cover codes for the observation ``cloudLayers`` amount. The
# main app maps these to a cloud-cover percentage.
CLOUD_AMOUNT_CHOICES = [
    ( 'CLR', 'CLR — Clear' ),
    ( 'FEW', 'FEW — Few' ),
    ( 'SCT', 'SCT — Scattered' ),
    ( 'BKN', 'BKN — Broken' ),
    ( 'OVC', 'OVC — Overcast' ),
]
