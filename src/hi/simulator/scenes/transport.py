"""Transport-pane context: the recording/playback bar + its timeline.

Assembles the context shared by the full Scenes dashboard render and the live
fragment-refresh endpoint, so the two can't drift. Also the button-relevant
signature the client polls to decide when to fragment-refresh.
"""
from .player import SimPlayer
from .recorder import SimRecorder
from .timeline import timeline_model


def _resolve_sequence( sequence_param, sequence_list ):
    if sequence_param:
        match = next(
            ( s for s in sequence_list if str( s.id ) == str( sequence_param )), None,
        )
        if match is not None:
            return match
    return sequence_list[ 0 ] if sequence_list else None


def build_transport_context( scene, sequence_param ):
    """Context for the transport pane (badge, controls, timeline) — shared by
    the full dashboard and the live fragment-refresh endpoint."""
    sequence_list = list( scene.state_sequences.all() )
    selected_sequence = _resolve_sequence( sequence_param, sequence_list )
    player_status = SimPlayer().get_status()
    timeline = None
    initial_state_count = 0
    if selected_sequence is not None:
        timeline = timeline_model( selected_sequence, player_status )
        initial_state_count = len( selected_sequence.initial_state_json or [] )
    return {
        'scene': scene,
        'sequence_list': sequence_list,
        'selected_sequence': selected_sequence,
        'recorder_status': SimRecorder().get_status(),
        'player_status': player_status,
        'timeline': timeline,
        'initial_state_count': initial_state_count,
    }


def transport_signature( recorder_status, player_status ):
    """A token of the *button-relevant* state, so the client only fragment-
    refreshes the transport when the available controls actually change (not
    on every playhead tick or step-count bump)."""
    return '{}|{}|{}|{}'.format(
        int( recorder_status[ 'recording' ] ),
        int( recorder_status[ 'paused' ] ),
        player_status[ 'mode' ],
        int( recorder_status[ 'has_working' ] ),
    )
