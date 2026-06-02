"""Choice lists for the Sunrise-Sunset.org simulator state editor.

Self-contained on purpose — the weather simulators do not import from
``hi.apps.weather`` (see ``payload_utils`` module docstring).
"""

# The API's top-level ``status`` field. The main-app parser raises
# unless this is exactly ``OK``; the error values are offered so an
# operator can exercise the main app's failure handling.
STATUS_CHOICES = [
    ( 'OK', 'OK' ),
    ( 'INVALID_REQUEST', 'INVALID_REQUEST' ),
    ( 'INVALID_DATE', 'INVALID_DATE' ),
    ( 'UNKNOWN_ERROR', 'UNKNOWN_ERROR' ),
    ( 'INVALID_TZID', 'INVALID_TZID' ),
]

# Minutes from sunrise/sunset to each twilight boundary. Derived rather
# than separately editable to keep the form to a few fields; add real
# controls only if a screenshot ever needs them.
TWILIGHT_OFFSETS_MINUTES = {
    'civil': 30,
    'nautical': 60,
    'astronomical': 90,
}
