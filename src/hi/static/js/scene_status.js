(function() {

    // Live transport poller for the Scenes page. Companion to simulator.js's
    // state-value poller (which keeps the control grid live); this one keeps
    // the playback/record transport live:
    //   - smoothly advances the timeline playhead + badge time (rAF between polls),
    //   - updates the recording step count,
    //   - fragment-refreshes the transport pane when its button set changes.

    const POLL_INTERVAL_MS = 1000;

    const State = {
        signature: null,
        playing: false,
        baseT: 0,
        baseAt: 0,
        limit: 0,   // interpolation ceiling: next mark while stepping, else total
    };

    function _transport() {
        return document.querySelector( '.sim-scene-transport[data-status-url]' );
    }

    function _renderPlayhead( t ) {
        const badge = document.querySelector( '.sim-scene-transport .js-playhead' );
        if ( badge ) { badge.textContent = ( Math.round( t * 10 ) / 10 ).toFixed( 1 ); }
        document.querySelectorAll( '.sim-timeline' ).forEach( function( container ) {
            if ( window.HiSceneTimeline ) { HiSceneTimeline.setPlayhead( container, t ); }
        });
    }

    function _tick() {
        if ( State.playing ) {
            const elapsed = ( window.performance.now() - State.baseAt ) / 1000;
            const t = Math.min( State.limit, State.baseT + elapsed );
            _renderPlayhead( t );
        }
        window.requestAnimationFrame( _tick );
    }

    function _refreshTransport( url ) {
        if ( ! url ) { return; }
        $.ajax({
            url: url, global: false, cache: false,
            success: function( html ) {
                const region = _transport();
                if ( region ) {
                    const wrap = document.createElement( 'div' );
                    wrap.innerHTML = html;
                    const fresh = wrap.firstElementChild;
                    if ( fresh ) { region.parentNode.replaceChild( fresh, region ); }
                }
                if ( window.HiSceneTimeline ) { HiSceneTimeline.refresh(); }
            },
        });
    }

    function _poll() {
        const region = _transport();
        if ( ! region ) { return; }
        const statusUrl = region.getAttribute( 'data-status-url' );
        const transportUrl = region.getAttribute( 'data-transport-url' );
        $.ajax({
            url: statusUrl, dataType: 'json', global: false, cache: false,
            success: function( data ) {
                // A button-relevant change: swap the whole pane, then resync
                // the playhead on the next poll against the fresh DOM.
                if ( State.signature !== null && data.signature !== State.signature ) {
                    State.signature = data.signature;
                    State.playing = false;
                    _refreshTransport( transportUrl );
                    return;
                }
                State.signature = data.signature;

                const rec = data.recorder;
                const player = data.player;
                if ( rec.recording ) {
                    const steps = document.querySelector( '.sim-scene-transport .js-rec-steps' );
                    if ( steps ) { steps.textContent = rec.step_count; }
                }
                State.playing = !! player.playing;
                State.limit = ( player.playhead_limit != null )
                    ? player.playhead_limit : ( player.total || 0 );
                State.baseT = player.playhead || 0;
                State.baseAt = window.performance.now();
                if ( ! State.playing ) { _renderPlayhead( State.baseT ); }
            },
            error: function( jqXHR, textStatus ) {
                if ( window.console ) { console.warn( 'Scene status poll failed:', textStatus ); }
            },
        });
    }

    $(document).ready( function() {
        if ( ! _transport() ) { return; }
        window.setInterval( _poll, POLL_INTERVAL_MS );
        window.requestAnimationFrame( _tick );
        _poll();
    });

})();
