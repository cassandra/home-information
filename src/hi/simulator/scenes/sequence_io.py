"""Sequence step-JSON validation and export naming.

Shared by the edit / import (validate ``steps_json``) and export (filename)
sequence endpoints. No HTTP.
"""
import json
import re


def parse_steps( raw ):
    """Validate edited/imported sequence JSON. Accepts either a bare list of
    steps or an export envelope ({name, steps}); returns (steps, error)."""
    try:
        data = json.loads( raw )
    except ( ValueError, TypeError ):
        return None, 'Not valid JSON.'
    if isinstance( data, dict ) and 'steps' in data:
        data = data[ 'steps' ]
    if not isinstance( data, list ):
        return None, 'Expected a JSON list of steps.'
    cleaned = []
    for index, step in enumerate( data ):
        if not isinstance( step, dict ):
            return None, f'Step {index} is not an object.'
        if step.get( 'end' ):
            if 't' not in step:
                return None, f'Step {index} (end) is missing "t".'
            try:
                cleaned.append({ 't': float( step[ 't' ] ), 'end': True })
            except ( TypeError, ValueError ):
                return None, f'Step {index} (end) has a non-numeric "t".'
            continue
        if 'marker' in step:
            marker = { 'marker': str( step[ 'marker' ] ) }
            if 't' in step:
                try:
                    marker[ 't' ] = float( step[ 't' ] )
                except ( TypeError, ValueError ):
                    return None, f'Marker {index} has a non-numeric "t".'
            cleaned.append( marker )
            continue
        missing = [ k for k in ( 't', 'module', 'entity', 'state' ) if k not in step ]
        if missing:
            return None, f'Step {index} is missing field(s): {", ".join( missing )}.'
        try:
            t = float( step[ 't' ] )
        except ( TypeError, ValueError ):
            return None, f'Step {index} has a non-numeric "t".'
        cleaned.append({
            't': t,
            'module': str( step[ 'module' ] ),
            'entity': str( step[ 'entity' ] ),
            'state': str( step[ 'state' ] ),
            'value': step.get( 'value' ),
        })
        continue
    return cleaned, None


def safe_filename( name ):
    slug = re.sub( r'[^A-Za-z0-9._-]+', '_', name.strip() ).strip( '_' )
    return slug or 'sequence'
