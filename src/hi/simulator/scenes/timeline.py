"""SVG timeline render model for a scene's state sequence.

Pure presentation: turns a ``SimStateSequence``'s ``steps_json`` (plus the
player's status) into the geometry the timeline template renders. No HTTP.
Geometry is in SVG viewBox units — the SVG scales to fit via
``preserveAspectRatio="none"`` and the click handler maps pixels back to time.
"""

# Timeline geometry, in SVG viewBox units.
TIMELINE_VBW = 1000
TIMELINE_HEIGHT = 72
TIMELINE_X0 = 48
TIMELINE_X1 = 952
TIMELINE_AXIS_Y = 44
TIMELINE_MARKER_TOP = TIMELINE_AXIS_Y - 22    # event arrows above the axis
TIMELINE_STEP_TIP_Y = TIMELINE_AXIS_Y + 3     # state-change arrows below the axis
TIMELINE_STEP_BASE_Y = TIMELINE_AXIS_Y + 21
TIMELINE_GLYPH_HALF = 8
TIMELINE_HIT_HALF = 10                         # generous transparent hover/click column


SERVICE_MODULE_PREFIX = 'hi.simulator.services.'


def _short_module( module ):
    module = module or ''
    if module.startswith( SERVICE_MODULE_PREFIX ):
        return module[ len( SERVICE_MODULE_PREFIX ): ]
    return module


def _timeline_x( t, total ):
    if total <= 0:
        return TIMELINE_X0
    frac = min( 1.0, max( 0.0, t / total ))
    return round( TIMELINE_X0 + frac * ( TIMELINE_X1 - TIMELINE_X0 ), 2 )


def timeline_model( sequence, player_status ):
    """Parse a sequence's steps into a render model for the SVG timeline.
    Markers are down-arrows above the axis; state changes are up-arrows below
    it; the end sentinel is an end-rule at the right edge. Each glyph gets a
    wide transparent hit column so it is easy to hover/click. Timed items sit
    at their own t; a legacy marker without a t falls back to the preceding
    timed step (start is the implicit 0, never materialized)."""
    steps = sequence.steps_json or []
    total = max( ( float( s[ 't' ] ) for s in steps if 't' in s ), default = 0.0 )
    entries = []
    last_t = 0.0
    for step in steps:
        if step.get( 'end' ):
            et = float( step.get( 't', last_t ))
            last_t = max( last_t, et )
            x = _timeline_x( et, total )
            entries.append({
                'kind': 'end',
                't': round( et, 3 ),
                'x': x,
                'hit_x': round( x - TIMELINE_HIT_HALF, 2 ),
                'hit_y': 0,
                'hit_h': TIMELINE_HEIGHT,
                'title': 'End  (@{:.2f}s)'.format( et ),
            })
            continue
        if 'marker' in step:
            mt = float( step[ 't' ] ) if 't' in step else last_t
            last_t = max( last_t, mt )
            x = _timeline_x( mt, total )
            entries.append({
                'kind': 'marker',
                't': round( mt, 3 ),
                'x': x,
                'hit_x': round( x - TIMELINE_HIT_HALF, 2 ),
                'hit_y': 0,
                'hit_h': TIMELINE_AXIS_Y,           # events: above the axis only
                'points': '{x0},{top} {x1},{top} {x},{tip}'.format(
                    x0 = x - TIMELINE_GLYPH_HALF, x1 = x + TIMELINE_GLYPH_HALF,
                    top = TIMELINE_MARKER_TOP, x = x, tip = TIMELINE_AXIS_Y,
                ),
                'title': '⚑ {}  (@{:.2f}s)'.format( step[ 'marker' ], mt ),
            })
            continue
        try:
            t = float( step.get( 't', last_t ))
        except ( TypeError, ValueError ):
            t = last_t
        last_t = max( last_t, t )
        x = _timeline_x( t, total )
        entries.append({
            'kind': 'step',
            't': round( t, 3 ),
            'x': x,
            'hit_x': round( x - TIMELINE_HIT_HALF, 2 ),
            'hit_y': TIMELINE_AXIS_Y,               # transitions: below the axis only
            'hit_h': TIMELINE_HEIGHT - TIMELINE_AXIS_Y,
            'points': '{x},{tip} {x0},{base} {x1},{base}'.format(
                x = x, tip = TIMELINE_STEP_TIP_Y,
                x0 = x - TIMELINE_GLYPH_HALF, x1 = x + TIMELINE_GLYPH_HALF,
                base = TIMELINE_STEP_BASE_Y,
            ),
            'title': '{:.2f}s  [{}] {}.{} = {}'.format(
                t, _short_module( step.get( 'module' )), step.get( 'entity' ),
                step.get( 'state' ), step.get( 'value' ),
            ),
        })
        continue

    active = bool(
        player_status.get( 'loaded' )
        and player_status.get( 'sequence_id' ) == sequence.id
    )
    playhead_t = player_status.get( 'playhead', 0.0 ) if active else 0.0
    return {
        'total': total,
        'entries': entries,
        'vbw': TIMELINE_VBW,
        'height': TIMELINE_HEIGHT,
        'x0': TIMELINE_X0,
        'x1': TIMELINE_X1,
        'axis_y': TIMELINE_AXIS_Y,
        'hit_w': 2 * TIMELINE_HIT_HALF,
        'end_y1': 2,
        'end_y2': TIMELINE_HEIGHT - 2,
        'playhead_y1': 6,
        'playhead_y2': TIMELINE_HEIGHT - 6,
        'playhead_t': round( playhead_t, 3 ),
        'playhead_x': _timeline_x( playhead_t, total ),
        'active': active,
    }
