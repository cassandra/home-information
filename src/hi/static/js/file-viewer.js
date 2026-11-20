(function() {

    window.Hi = window.Hi || {};

    /*
      FILE VIEWER

      - Shows an app-served file in a full-screen overlay instead of a
        new tab. Any element carrying Hi.FILE_VIEWER_URL_ATTR opens it on
        click; the server renders those attributes (file_viewer_attrs),
        including the kind of viewing, from the file's MIME type.
      - The overlay markup is server-rendered once per page
        (panes/file_viewer.html). This module only shows one region at a
        time, fills slots, and sets media sources; it builds no markup.
      - The overlay stacks above any open Bootstrap modal without closing
        it, so the page and modal state (unsaved edits, tabs, scroll) are
        untouched. Two Bootstrap behaviors would interfere: the modal's
        focus trap (a document-level focusin handler that pulls focus
        back into the modal) and its Escape-to-close. The trap is
        switched off while the viewer is open and re-armed on close;
        it cannot be blocked from the overlay, since jQuery listens for
        focusin in the capture phase. Escape is taken in the capture
        phase while the viewer is open.
      - Each open is a session. Closing aborts the session's signal,
        which cancels its fetch and removes its media listeners, so late
        events from an earlier file cannot touch a later one.
      - Zoom steps are multiples of the fitted size. Fit never enlarges
        an image beyond its natural size.
    */

    // FileViewerKind external names (hi.apps.common.file_viewer).
    const KIND = {
        IMAGE       : 'image',
        VIDEO       : 'video',
        AUDIO       : 'audio',
        TEXT        : 'text',
        UNSUPPORTED : 'unsupported'
    };

    const STATE_REGION = {
        LOADING : 'loading',
        ERROR   : 'error'
    };

    const ACTION = {
        CLOSE    : 'close',
        ZOOM_IN  : 'zoom-in',
        ZOOM_OUT : 'zoom-out',
        ZOOM_FIT : 'zoom-fit'
    };

    const SLOT = {
        TITLE      : 'title',
        SUBTITLE   : 'subtitle',
        FILENAME   : 'filename',
        MIME_TYPE  : 'mime-type',
        SIZE       : 'size',
        TEXT       : 'text',
        ZOOM_LEVEL : 'zoom-level'
    };

    const REGION_ATTR = 'data-file-viewer-region';
    const SLOT_ATTR = 'data-file-viewer-slot';
    const ACTION_ATTR = 'data-file-viewer-action';
    const TOOLBAR_ATTR = 'data-file-viewer-toolbar';
    const SCROLL_ATTR = 'data-file-viewer-scroll';
    const STAGE_ATTR = 'data-file-viewer-stage';
    const MEDIA_ATTR = 'data-file-viewer-media';

    const OPEN_ROOT_CLASS = 'hi-file-viewer-open';

    // Bootstrap 4 modal internals (bootstrap.js, Modal._enforceFocus).
    const BOOTSTRAP_FOCUS_TRAP_EVENT = 'focusin.bs.modal';
    const BOOTSTRAP_MODAL_DATA_KEY = 'bs.modal';
    const SHOWN_MODAL_SELECTOR = '.modal.show';

    const ZOOM_STEPS = [ 1, 1.5, 2, 3, 4 ];
    const ZOOMABLE_KINDS = new Set([ KIND.IMAGE ]);

    // Larger text files are not worth reading into the page.
    const TEXT_MAX_BYTES = 1024 * 1024;

    const HiFileViewer = {
        open: function( triggerElement ) {
            _open( triggerElement );
        },
        close: function() {
            _close();
        },
        isOpen: function() {
            return Boolean( _session );
        },
        nextZoomIndex: function( zoomIndex, action ) {
            return _nextZoomIndex( zoomIndex, action );
        }
    };

    window.Hi.fileViewer = HiFileViewer;

    let _viewerElement = null;
    let _session = null;   // { file, trigger, zoomIndex, abortController }

    /* Elements */

    function _viewer() {
        if ( ! _viewerElement || ! _viewerElement.isConnected ) {
            _viewerElement = document.getElementById( Hi.FILE_VIEWER_ID );
        }
        return _viewerElement;
    }

    function _region( name ) {
        return _viewer().querySelector( '[' + REGION_ATTR + '="' + name + '"]' );
    }

    function _slot( name ) {
        return _viewer().querySelector( '[' + SLOT_ATTR + '="' + name + '"]' );
    }

    function _media( kind ) {
        return _region( kind ).querySelector( '[' + MEDIA_ATTR + ']' );
    }

    function _toolbar() {
        return _viewer().querySelector( '[' + TOOLBAR_ATTR + ']' );
    }

    /* Opening and closing */

    function _fileOf( triggerElement ) {
        return {
            url      : triggerElement.getAttribute( Hi.FILE_VIEWER_URL_ATTR ),
            kind     : triggerElement.getAttribute( Hi.FILE_VIEWER_KIND_ATTR ) || KIND.UNSUPPORTED,
            title    : triggerElement.getAttribute( Hi.FILE_VIEWER_TITLE_ATTR ) || '',
            filename : triggerElement.getAttribute( Hi.FILE_VIEWER_FILENAME_ATTR ) || '',
            mimeType : triggerElement.getAttribute( Hi.FILE_VIEWER_MIME_TYPE_ATTR ) || '',
            size     : triggerElement.getAttribute( Hi.FILE_VIEWER_SIZE_ATTR ) || ''
        };
    }

    function _open( triggerElement ) {
        if ( ! _viewer() ) {
            return;
        }
        _close();
        const file = _fileOf( triggerElement );
        _session = {
            file            : file,
            trigger         : triggerElement,
            zoomIndex       : 0,
            abortController : new AbortController()
        };

        // A focused field would keep the on-screen keyboard up.
        if ( document.activeElement instanceof HTMLElement ) {
            document.activeElement.blur();
        }
        _fillHeader( file );
        _suspendModalFocusTrap();
        document.documentElement.classList.add( OPEN_ROOT_CLASS );
        _viewer().hidden = false;
        _showRegion( STATE_REGION.LOADING );
        _viewer().querySelector( '[' + ACTION_ATTR + '="' + ACTION.CLOSE + '"]' ).focus();

        const loader = LOADERS[ file.kind ] || _loadUnsupported;
        loader( _session );
    }

    function _close() {
        if ( ! _session ) {
            return;
        }
        const session = _session;
        _session = null;
        session.abortController.abort();
        _clearContent();
        _viewer().hidden = true;
        document.documentElement.classList.remove( OPEN_ROOT_CLASS );
        _restoreModalFocusTrap();
        if ( session.trigger.isConnected ) {
            session.trigger.focus({ preventScroll: true });
        }
    }

    function _suspendModalFocusTrap() {
        $( document ).off( BOOTSTRAP_FOCUS_TRAP_EVENT );
    }

    function _restoreModalFocusTrap() {
        const modal = $( SHOWN_MODAL_SELECTOR ).last().data( BOOTSTRAP_MODAL_DATA_KEY );
        if ( modal ) {
            modal._enforceFocus();
        }
    }

    function _clearContent() {
        [ KIND.VIDEO, KIND.AUDIO ].forEach( function( kind ) {
            const mediaElement = _media( kind );
            mediaElement.pause();
            mediaElement.removeAttribute( 'src' );
            mediaElement.load();
        });
        const imageElement = _media( KIND.IMAGE );
        imageElement.removeAttribute( 'src' );
        imageElement.style.width = '';
        imageElement.style.height = '';
        _slot( SLOT.TEXT ).textContent = '';
        _toolbar().hidden = true;
    }

    function _fillHeader( file ) {
        _slot( SLOT.TITLE ).textContent = file.title;
        const subtitleElement = _slot( SLOT.SUBTITLE );
        subtitleElement.textContent = [ file.filename, file.mimeType, file.size ]
            .filter( Boolean )
            .join( subtitleElement.dataset.separator );
    }

    function _showRegion( name ) {
        _viewer().querySelectorAll( '[' + REGION_ATTR + ']' ).forEach( function( regionElement ) {
            regionElement.hidden = ( regionElement.getAttribute( REGION_ATTR ) !== name );
        });
    }

    // Runs a session's handler only while that session is still open.
    function _ifCurrent( session, handler ) {
        return function( value ) {
            if ( session === _session ) {
                handler( value );
            }
        };
    }

    function _showError() {
        _toolbar().hidden = true;
        _showRegion( STATE_REGION.ERROR );
    }

    /* Loaders, one per kind */

    function _loadImage( session ) {
        const imageElement = _media( KIND.IMAGE );
        const options = { once: true, signal: session.abortController.signal };
        imageElement.addEventListener( 'load', _ifCurrent( session, function() {
            _showRegion( KIND.IMAGE );
            _toolbar().hidden = false;
            _applyZoom();
        }), options );
        imageElement.addEventListener( 'error', _ifCurrent( session, _showError ), options );
        imageElement.src = session.file.url;
    }

    function _loadMedia( session, kind ) {
        const mediaElement = _media( kind );
        const options = { once: true, signal: session.abortController.signal };
        mediaElement.addEventListener( 'loadedmetadata', _ifCurrent( session, function() {
            _showRegion( kind );
        }), options );
        mediaElement.addEventListener( 'error', _ifCurrent( session, _showError ), options );
        mediaElement.src = session.file.url;
    }

    function _loadText( session ) {
        _fetchTextWithinLimit( session.file.url, session.abortController.signal ).then(
            _ifCurrent( session, function( text ) {
                if ( text === null ) {
                    _loadUnsupported( session );
                    return;
                }
                _slot( SLOT.TEXT ).textContent = text;
                _showRegion( KIND.TEXT );
            }),
            _ifCurrent( session, _showError )
        );
    }

    // Resolves to the text, or to null when it exceeds TEXT_MAX_BYTES.
    // Reads incrementally so an oversized file is not fully downloaded.
    async function _fetchTextWithinLimit( url, signal ) {
        const response = await fetch( url, { signal: signal } );
        if ( ! response.ok ) {
            throw new Error( 'File request failed: ' + response.status );
        }
        const declaredLength = Number( response.headers.get( 'Content-Length' ));
        if ( declaredLength > TEXT_MAX_BYTES ) {
            response.body.cancel();
            return null;
        }
        const reader = response.body.getReader();
        const chunks = [];
        let totalBytes = 0;
        while ( true ) {
            const { done, value } = await reader.read();
            if ( done ) {
                break;
            }
            totalBytes += value.length;
            if ( totalBytes > TEXT_MAX_BYTES ) {
                reader.cancel();
                return null;
            }
            chunks.push( value );
        }
        return new TextDecoder().decode( await new Blob( chunks ).arrayBuffer() );
    }

    function _loadUnsupported( session ) {
        const file = session.file;
        _fillDetail( SLOT.FILENAME, file.filename );
        _fillDetail( SLOT.MIME_TYPE, file.mimeType );
        _fillDetail( SLOT.SIZE, file.size );
        _showRegion( KIND.UNSUPPORTED );
    }

    function _fillDetail( slotName, value ) {
        const slotElement = _slot( slotName );
        slotElement.textContent = value || slotElement.dataset.emptyText;
    }

    const LOADERS = {
        [ KIND.IMAGE ]       : _loadImage,
        [ KIND.VIDEO ]       : function( session ) { _loadMedia( session, KIND.VIDEO ); },
        [ KIND.AUDIO ]       : function( session ) { _loadMedia( session, KIND.AUDIO ); },
        [ KIND.TEXT ]        : _loadText,
        [ KIND.UNSUPPORTED ] : _loadUnsupported
    };

    /* Zoom */

    function _nextZoomIndex( zoomIndex, action ) {
        if ( action === ACTION.ZOOM_FIT ) {
            return 0;
        }
        const step = ( action === ACTION.ZOOM_IN ) ? 1 : -1;
        return Math.min( ZOOM_STEPS.length - 1, Math.max( 0, zoomIndex + step ));
    }

    function _zoom( action ) {
        if ( ! _session || ! ZOOMABLE_KINDS.has( _session.file.kind )) {
            return;
        }
        _session.zoomIndex = _nextZoomIndex( _session.zoomIndex, action );
        _applyZoom();
    }

    function _applyZoom() {
        const zoomIndex = _session.zoomIndex;
        _updateZoomControls( zoomIndex );
        _resizeImage( ZOOM_STEPS[ zoomIndex ] );
    }

    function _updateZoomControls( zoomIndex ) {
        _slot( SLOT.ZOOM_LEVEL ).textContent = Math.round( ZOOM_STEPS[ zoomIndex ] * 100 ) + '%';
        const isFit = ( zoomIndex === 0 );
        const isMax = ( zoomIndex === ZOOM_STEPS.length - 1 );
        _toolbar().querySelector( '[' + ACTION_ATTR + '="' + ACTION.ZOOM_OUT + '"]' ).disabled = isFit;
        _toolbar().querySelector( '[' + ACTION_ATTR + '="' + ACTION.ZOOM_FIT + '"]' ).disabled = isFit;
        _toolbar().querySelector( '[' + ACTION_ATTR + '="' + ACTION.ZOOM_IN + '"]' ).disabled = isMax;
    }

    // Sizes the image to the zoom factor over its fitted size, keeping
    // the point at the center of the view in place.
    function _resizeImage( zoomFactor ) {
        const regionElement = _region( KIND.IMAGE );
        const scrollElement = regionElement.querySelector( '[' + SCROLL_ATTR + ']' );
        const stageStyle = getComputedStyle( regionElement.querySelector( '[' + STAGE_ATTR + ']' ));
        const imageElement = _media( KIND.IMAGE );

        const centerX = ( scrollElement.scrollLeft + scrollElement.clientWidth / 2 ) / scrollElement.scrollWidth;
        const centerY = ( scrollElement.scrollTop + scrollElement.clientHeight / 2 ) / scrollElement.scrollHeight;

        const availableWidth = scrollElement.clientWidth
              - parseFloat( stageStyle.paddingLeft ) - parseFloat( stageStyle.paddingRight );
        const availableHeight = scrollElement.clientHeight
              - parseFloat( stageStyle.paddingTop ) - parseFloat( stageStyle.paddingBottom );
        const fitScale = Math.min( availableWidth / imageElement.naturalWidth,
                                   availableHeight / imageElement.naturalHeight,
                                   1 );
        imageElement.style.width = Math.round( imageElement.naturalWidth * fitScale * zoomFactor ) + 'px';
        imageElement.style.height = Math.round( imageElement.naturalHeight * fitScale * zoomFactor ) + 'px';

        scrollElement.scrollLeft = centerX * scrollElement.scrollWidth - scrollElement.clientWidth / 2;
        scrollElement.scrollTop = centerY * scrollElement.scrollHeight - scrollElement.clientHeight / 2;
    }

    /* Keyboard: Escape closes; Tab stays within the viewer. */

    function _handleKeydown( event ) {
        if ( ! _session ) {
            return;
        }
        if ( event.key === 'Escape' ) {
            event.preventDefault();
            event.stopImmediatePropagation();
            _close();
        } else if ( event.key === 'Tab' ) {
            _keepTabFocusInside( event );
        }
    }

    function _keepTabFocusInside( event ) {
        const focusable = Array.from( _viewer().querySelectorAll( 'button, video, audio' ))
              .filter( function( element ) {
                  return ! element.disabled && element.getClientRects().length > 0;
              });
        if ( focusable.length === 0 ) {
            return;
        }
        const first = focusable[ 0 ];
        const last = focusable[ focusable.length - 1 ];
        const isInside = _viewer().contains( document.activeElement );
        if ( event.shiftKey && ( document.activeElement === first || ! isInside )) {
            event.preventDefault();
            last.focus();
        } else if ( ! event.shiftKey && ( document.activeElement === last || ! isInside )) {
            event.preventDefault();
            first.focus();
        }
    }

    /* Event wiring */

    function _handleClick( event ) {
        if ( ! ( event.target instanceof Element )) {
            return;
        }
        const actionElement = event.target.closest( '[' + ACTION_ATTR + ']' );
        if ( actionElement && _viewer() && _viewer().contains( actionElement )) {
            const action = actionElement.getAttribute( ACTION_ATTR );
            if ( action === ACTION.CLOSE ) {
                _close();
            } else {
                _zoom( action );
            }
            return;
        }
        const triggerElement = event.target.closest( '[' + Hi.FILE_VIEWER_URL_ATTR + ']' );
        if ( triggerElement ) {
            event.preventDefault();
            _open( triggerElement );
        }
    }

    function _handleResize() {
        if ( _session && ZOOMABLE_KINDS.has( _session.file.kind ) && ! _region( _session.file.kind ).hidden ) {
            _applyZoom();
        }
    }

    document.addEventListener( 'click', _handleClick );
    document.addEventListener( 'keydown', _handleKeydown, true );
    window.addEventListener( 'resize', _handleResize );

})();
