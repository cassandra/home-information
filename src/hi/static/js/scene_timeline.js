(function() {

    // Annotated sequence timeline: click-to-jump (posts a seek), plus a
    // setPlayhead() hook the status poller will drive once polling lands.
    const HiSceneTimeline = {
        setPlayhead: function( container, t ) { return _setPlayhead( container, t ); },
        refresh: function() { return _initAll(); },
    };
    window.HiSceneTimeline = HiSceneTimeline;

    function _geom( container ) {
        return {
            total: parseFloat( container.getAttribute( 'data-total' )) || 0,
            x0: parseFloat( container.getAttribute( 'data-x0' )),
            x1: parseFloat( container.getAttribute( 'data-x1' )),
            vbw: parseFloat( container.getAttribute( 'data-vbw' )),
        };
    }

    function _timeToX( g, t ) {
        if ( g.total <= 0 ) { return g.x0; }
        let frac = Math.max( 0, Math.min( 1, t / g.total ));
        return g.x0 + frac * ( g.x1 - g.x0 );
    }

    function _xToTime( container, clientX ) {
        const svg = container.querySelector( '.sim-timeline-svg' );
        const g = _geom( container );
        const rect = svg.getBoundingClientRect();
        if ( rect.width <= 0 || g.total <= 0 ) { return 0; }
        const userX = (( clientX - rect.left ) / rect.width ) * g.vbw;
        const t = ( userX - g.x0 ) / ( g.x1 - g.x0 ) * g.total;
        return Math.max( 0, Math.min( g.total, t ));
    }

    function _submitSeek( container, t ) {
        const form = container.querySelector( '.sim-timeline-seek-form' );
        if ( ! form ) { return; }
        const field = form.querySelector( 'input[name="t"]' );
        if ( ! field ) { return; }
        field.value = t.toFixed( 3 );
        form.submit();
    }

    function _setPlayhead( container, t ) {
        const line = container.querySelector( '[data-role="playhead"]' );
        if ( ! line ) { return; }
        const x = _timeToX( _geom( container ), t );
        line.setAttribute( 'x1', x );
        line.setAttribute( 'x2', x );
        line.style.display = '';
    }

    function _ancestorAttr( container, target, attr ) {
        // Walk up from the event target to the glyph group carrying attr.
        let node = target;
        while ( node && node !== container ) {
            if ( node.getAttribute && node.hasAttribute && node.hasAttribute( attr )) {
                return node.getAttribute( attr );
            }
            node = node.parentNode;
        }
        return null;
    }

    function _exactTimeFromTarget( container, target ) {
        const value = _ancestorAttr( container, target, 'data-t' );
        return ( value === null ) ? null : parseFloat( value );
    }

    function _tooltip( container ) {
        let tip = container.querySelector( '.sim-timeline-tooltip' );
        if ( ! tip ) {
            tip = document.createElement( 'div' );
            tip.className = 'sim-timeline-tooltip';
            tip.style.display = 'none';
            container.appendChild( tip );
        }
        return tip;
    }

    function _showTip( container, evt ) {
        const text = _ancestorAttr( container, evt.target, 'data-title' );
        const tip = _tooltip( container );
        if ( text === null ) { tip.style.display = 'none'; return; }
        tip.textContent = text;
        tip.style.display = 'block';
        const rect = container.getBoundingClientRect();
        let left = evt.clientX - rect.left + 12;
        let top = evt.clientY - rect.top + 14;
        const maxLeft = container.clientWidth - tip.offsetWidth - 4;
        if ( left > maxLeft ) { left = Math.max( 0, maxLeft ); }
        tip.style.left = left + 'px';
        tip.style.top = top + 'px';
    }

    function _hideTip( container ) {
        const tip = container.querySelector( '.sim-timeline-tooltip' );
        if ( tip ) { tip.style.display = 'none'; }
    }

    function _onClick( container, evt ) {
        let t = _exactTimeFromTarget( container, evt.target );
        if ( t === null ) { t = _xToTime( container, evt.clientX ); }
        _submitSeek( container, t );
    }

    function _initAll() {
        document.querySelectorAll( '.sim-timeline' ).forEach( function( container ) {
            if ( container.__hiTimelineBound ) { return; }
            container.__hiTimelineBound = true;
            const svg = container.querySelector( '.sim-timeline-svg' );
            if ( ! svg ) { return; }
            svg.addEventListener( 'click', function( evt ) { _onClick( container, evt ); });
            svg.addEventListener( 'mousemove', function( evt ) { _showTip( container, evt ); });
            svg.addEventListener( 'mouseleave', function() { _hideTip( container ); });
        });
    }

    $(document).ready( _initAll );

})();
