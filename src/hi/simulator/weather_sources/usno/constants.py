"""Choice lists for the USNO simulator state editor.

Self-contained on purpose — the weather simulators do not import from
``hi.apps.weather`` (see ``payload_utils`` module docstring).

The main app derives the moon's waxing/waning flag from the phase name
substring (``waxing`` / ``waning`` / ``new`` / ``full`` / ``first`` /
``last``), so these standard names all map cleanly.
"""

MOON_PHASE_CHOICES = [
    ( 'New Moon', 'New Moon' ),
    ( 'Waxing Crescent', 'Waxing Crescent' ),
    ( 'First Quarter', 'First Quarter' ),
    ( 'Waxing Gibbous', 'Waxing Gibbous' ),
    ( 'Full Moon', 'Full Moon' ),
    ( 'Waning Gibbous', 'Waning Gibbous' ),
    ( 'Last Quarter', 'Last Quarter' ),
    ( 'Waning Crescent', 'Waning Crescent' ),
]
