/* Location SVG Editor Javascript */

(function() {

    window.Hi = window.Hi || {};
    window.Hi.SvgEdit = window.Hi.SvgEdit || {};
    window.Hi.SvgEdit.snapGridPixels = 5;

    const SVG_NS = 'http://www.w3.org/2000/svg';

    /* Element IDs (must match DIVID values in constants.py and templates) */
    const PALETTE_CONTAINER_ID = 'hi-svg-edit-palette';
    const CANVAS_SVG_ID = 'hi-svg-edit-svg';
    const CANVAS_AREA_ID = 'hi-svg-edit-canvas';
    const CANVAS_CONTAINER_ID = 'hi-svg-edit-canvas-container';
    const CONFORMANCE_WARNING_ID = 'hi-svg-edit-conformance-warning';

    /* SVG element attributes and classes (shared with SVG templates and saved files) */
    const BG_ELEMENT_CLASS = 'hi-bg-element';
    const BG_HIT_AREA_CLASS = 'hi-bg-hit-area';
    const BG_EDITOR_ATTR = 'data-hi-editor';
    const BG_TYPE_ATTR = 'data-bg-type';
    const BG_EDIT_TYPE_ATTR = 'data-bg-edit-type';
    const BG_LAYER_ATTR = 'data-bg-layer';

    /* Palette template attributes (read from <defs>) */
    const BG_LABEL_ATTR = 'data-bg-label';
    const BG_CATEGORY_ATTR = 'data-bg-category';
    const BG_TEMPLATE_ID_ATTR = 'data-bg-template-id';

    /* Palette CSS classes (JS-generated DOM + location-svg-edit.css) */
    const PALETTE_CATEGORY_CLASS = 'hi-palette-category';
    const PALETTE_CATEGORY_LABEL_CLASS = 'hi-palette-category-label';
    const PALETTE_ITEMS_CLASS = 'hi-palette-items';
    const PALETTE_ITEM_CLASS = 'hi-palette-item';
    const PALETTE_LABEL_CLASS = 'hi-palette-label';
    const PALETTE_SWATCH_CLASS = 'hi-palette-swatch';

    const CATEGORY_ORDER = ['structural', 'features', 'exterior'];
    const CATEGORY_LABELS = {
        structural: 'Structural',
        features: 'Features',
        exterior: 'Exterior',
    };

    /* Viewbox dimensions for palette swatch mini-SVGs by edit type. */
    const SWATCH_VIEWBOX = {
        closed: { padding: 4 },
        open: { height: 20, padding: 4 },
        icon: { padding: 4 },
    };

    const SWATCH_WIDTH = 44;
    const SWATCH_HEIGHT = 32;

    function buildPalette() {
        var canvasSvg = document.getElementById(CANVAS_SVG_ID);
        if (!canvasSvg) {
            return;
        }

        /* Find the palette defs — the <defs> that contains <g> children
           with data-bg-edit-type attributes (as opposed to the fill pattern defs). */
        var defsElement = null;
        var allDefs = canvasSvg.querySelectorAll('defs');
        for (var di = 0; di < allDefs.length; di++) {
            if (allDefs[di].querySelector('g[' + BG_EDIT_TYPE_ATTR + ']')) {
                defsElement = allDefs[di];
                break;
            }
        }
        if (!defsElement) {
            return;
        }

        var templates = [];
        $(defsElement).children('g').each(function() {
            var editType = $(this).attr(BG_EDIT_TYPE_ATTR);
            if (!editType) {
                return;
            }
            templates.push({
                id: $(this).attr('id'),
                editType: editType,
                label: $(this).attr(BG_LABEL_ATTR) || '',
                category: $(this).attr(BG_CATEGORY_ATTR) || '',
                layer: parseInt($(this).attr(BG_LAYER_ATTR) || '0', 10),
                element: this,
            });
        });

        /* Group by category. */
        var categories = {};
        for (var i = 0; i < templates.length; i++) {
            var tmpl = templates[i];
            if (!categories[tmpl.category]) {
                categories[tmpl.category] = [];
            }
            categories[tmpl.category].push(tmpl);
        }

        var container = document.getElementById(PALETTE_CONTAINER_ID);
        if (!container) {
            return;
        }

        for (var ci = 0; ci < CATEGORY_ORDER.length; ci++) {
            var catKey = CATEGORY_ORDER[ci];
            var catTemplates = categories[catKey];
            if (!catTemplates || catTemplates.length === 0) {
                continue;
            }

            var catDiv = document.createElement('div');
            catDiv.className = PALETTE_CATEGORY_CLASS;

            var catLabel = document.createElement('span');
            catLabel.className = PALETTE_CATEGORY_LABEL_CLASS;
            catLabel.textContent = CATEGORY_LABELS[catKey] || catKey;
            catDiv.appendChild(catLabel);

            var itemsDiv = document.createElement('div');
            itemsDiv.className = PALETTE_ITEMS_CLASS;

            for (var ti = 0; ti < catTemplates.length; ti++) {
                var tmpl = catTemplates[ti];
                var itemDiv = createPaletteItem(tmpl);
                itemsDiv.appendChild(itemDiv);
            }

            catDiv.appendChild(itemsDiv);
            container.appendChild(catDiv);
        }
    }

    function createPaletteItem(tmpl) {
        var itemDiv = document.createElement('div');
        itemDiv.className = PALETTE_ITEM_CLASS;
        itemDiv.setAttribute(BG_TEMPLATE_ID_ATTR, tmpl.id);
        itemDiv.setAttribute('draggable', 'true');
        itemDiv.setAttribute('title', tmpl.label);

        itemDiv.addEventListener('dragstart', function(event) {
            event.dataTransfer.setData('text/plain', tmpl.id);
            event.dataTransfer.effectAllowed = 'copy';
        });

        var swatchSvg = createSwatchSvg(tmpl);
        itemDiv.appendChild(swatchSvg);

        var label = document.createElement('span');
        label.className = PALETTE_LABEL_CLASS;
        label.textContent = tmpl.label;
        itemDiv.appendChild(label);

        return itemDiv;
    }

    function createSwatchSvg(tmpl) {
        var svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('class', PALETTE_SWATCH_CLASS);
        svg.setAttribute('width', SWATCH_WIDTH);
        svg.setAttribute('height', SWATCH_HEIGHT);

        /* Clone the template content into the swatch. */
        var paths = tmpl.element.querySelectorAll('path');
        for (var i = 0; i < paths.length; i++) {
            var clone = paths[i].cloneNode(true);
            svg.appendChild(clone);
        }

        /* Compute viewBox from template geometry. */
        var viewBox = computeSwatchViewBox(tmpl);
        svg.setAttribute('viewBox', viewBox);

        return svg;
    }

    function computeSwatchViewBox(tmpl) {
        var pad = SWATCH_VIEWBOX[tmpl.editType]
            ? SWATCH_VIEWBOX[tmpl.editType].padding
            : 4;

        /* Parse all path d attributes to find bounding box. */
        var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        var paths = tmpl.element.querySelectorAll('path');
        for (var i = 0; i < paths.length; i++) {
            var coords = paths[i].getAttribute('d').match(/[\d.]+/g);
            if (!coords) {
                continue;
            }
            for (var j = 0; j < coords.length; j += 2) {
                var x = parseFloat(coords[j]);
                var y = parseFloat(coords[j + 1]);
                if (!isNaN(x) && !isNaN(y)) {
                    if (x < minX) { minX = x; }
                    if (y < minY) { minY = y; }
                    if (x > maxX) { maxX = x; }
                    if (y > maxY) { maxY = y; }
                }
            }
        }

        if (minX === Infinity) {
            return '0 0 100 100';
        }

        /* For open paths (lines), ensure minimum height for visibility. */
        var width = maxX - minX;
        var height = maxY - minY;
        if (tmpl.editType === 'open' && height < 20) {
            var midY = (minY + maxY) / 2;
            minY = midY - 10;
            height = 20;
        }

        return (minX - pad) + ' ' + (minY - pad) + ' ' + (width + pad * 2) + ' ' + (height + pad * 2);
    }

    /* ==================== */
    /* Element Delete       */
    /* ==================== */

    Hi.SvgEdit.onElementDeleted = function() {
        saveDraft();
    };

    /* ==================== */
    /* Undo                 */
    /* ==================== */

    var UNDO_STACK_MAX = 20;
    var gUndoStack = [];
    var gLastSavedSnapshot = null;

    function getCleanSnapshot() {
        var canvasSvg = document.getElementById( CANVAS_SVG_ID );
        if ( ! canvasSvg ) { return null; }

        var editorGroup = canvasSvg.querySelector( 'g[' + BG_EDITOR_ATTR + ']' );
        if ( ! editorGroup ) { return null; }

        var clone = editorGroup.cloneNode( true );
        cleanCloneForSave( clone );
        return clone.outerHTML;
    }

    function pushUndoSnapshot() {
        var snapshot = gLastSavedSnapshot;
        if ( ! snapshot ) {
            snapshot = getCleanSnapshot();
        }
        if ( ! snapshot ) { return; }

        if ( gUndoStack.length >= UNDO_STACK_MAX ) {
            gUndoStack.shift();
        }
        gUndoStack.push( snapshot );
    }

    Hi.SvgEdit.undo = function() {
        if ( gUndoStack.length === 0 ) { return false; }

        Hi.SvgIconCore.clearSelection();
        Hi.SvgPathCore.clearSelection();

        var snapshot = gUndoStack.pop();
        var canvasSvg = document.getElementById( CANVAS_SVG_ID );
        if ( ! canvasSvg ) { return false; }

        var editorGroup = canvasSvg.querySelector( 'g[' + BG_EDITOR_ATTR + ']' );
        if ( ! editorGroup ) { return false; }

        editorGroup.outerHTML = snapshot;
        gLastSavedSnapshot = snapshot;

        /* Persist the restored state to the draft file. */
        if ( Hi.SvgEdit.saveUrl ) {
            $.post( Hi.SvgEdit.saveUrl, {
                svg_content: snapshot,
                csrfmiddlewaretoken: Hi.SvgEdit.csrfToken,
            });
        }
        return true;
    };

    Hi.SvgEdit.hasUndo = function() {
        return gUndoStack.length > 0;
    };

    /* ==================== */
    /* Draft Save           */
    /* ==================== */

    function cleanCloneForSave( clone ) {
        /* Remove proxy path editing containers. */
        var proxies = clone.querySelectorAll( '#' + Hi.SvgPathCore.PROXY_PATH_CONTAINER_ID );
        for ( var i = 0; i < proxies.length; i++ ) {
            proxies[i].parentNode.removeChild( proxies[i] );
        }

        /* Remove editing highlight classes. */
        var highlighted = clone.querySelectorAll( '.' + Hi.HIGHLIGHTED_CLASS );
        for ( var i = 0; i < highlighted.length; i++ ) {
            highlighted[i].classList.remove( Hi.HIGHLIGHTED_CLASS );
        }

        /* Remove action-state attributes. */
        var withActionState = clone.querySelectorAll( '[action-state]' );
        for ( var i = 0; i < withActionState.length; i++ ) {
            withActionState[i].removeAttribute( 'action-state' );
        }

        /* Remove any display:none from hidden path groups (during proxy editing). */
        var hidden = clone.querySelectorAll( '[style*="display"]' );
        for ( var i = 0; i < hidden.length; i++ ) {
            hidden[i].style.removeProperty( 'display' );
            if ( ! hidden[i].getAttribute( 'style' ) ) {
                hidden[i].removeAttribute( 'style' );
            }
        }
    }

    function saveDraft() {
        var canvasSvg = document.getElementById( CANVAS_SVG_ID );
        if ( ! canvasSvg ) { return; }

        var editorGroup = canvasSvg.querySelector( 'g[' + BG_EDITOR_ATTR + ']' );
        if ( ! editorGroup ) { return; }

        pushUndoSnapshot();

        /* Clone and clean: serialize a pristine copy without editing artifacts. */
        var clone = editorGroup.cloneNode( true );
        cleanCloneForSave( clone );
        var svgContent = clone.outerHTML;

        gLastSavedSnapshot = svgContent;

        if ( ! Hi.SvgEdit.saveUrl ) { return; }

        $.post( Hi.SvgEdit.saveUrl, {
            svg_content: svgContent,
            csrfmiddlewaretoken: Hi.SvgEdit.csrfToken,
        });
    }

    /* ==================== */
    /* Palette Drop         */
    /* ==================== */

    function initPaletteDrop() {
        var $canvas = $( '#' + CANVAS_AREA_ID );

        $canvas.on( 'dragover', function( event ) {
            event.preventDefault();
            event.originalEvent.dataTransfer.dropEffect = 'copy';
        });

        $canvas.on( 'drop', function( event ) {
            event.preventDefault();
            var templateId = event.originalEvent.dataTransfer.getData( 'text/plain' );
            if ( ! templateId ) { return; }

            var templateElement = document.getElementById( templateId );
            if ( ! templateElement ) { return; }

            var canvasSvg = document.getElementById( CANVAS_SVG_ID );
            if ( ! canvasSvg ) { return; }

            /* Convert drop screen coordinates to SVG coordinates. */
            var svgPoint = Hi.svgUtils.toSvgPoint(
                $( canvasSvg ), event.originalEvent.clientX, event.originalEvent.clientY
            );

            var editType = $( templateElement ).attr( BG_EDIT_TYPE_ATTR );
            var bgType = templateId.replace( /^hi-/, '' );
            var layer = parseInt( $( templateElement ).attr( BG_LAYER_ATTR ) || '0', 10 );

            var newElement = createElementFromTemplate( templateElement, bgType, editType, layer, svgPoint );
            if ( newElement ) {
                insertAtLayer( canvasSvg, newElement, layer );
                saveDraft();
            }
        });
    }

    function generateBgId() {
        var hex = Math.random().toString(16).substring(2, 10);
        return 'bg-' + hex;
    }

    function createElementFromTemplate( templateElement, bgType, editType, layer, svgPoint ) {
        var SVG_NS = 'http://www.w3.org/2000/svg';
        var group = document.createElementNS( SVG_NS, 'g' );
        group.setAttribute( 'id', generateBgId() );
        group.setAttribute( 'class', BG_ELEMENT_CLASS );
        group.setAttribute( BG_TYPE_ATTR, bgType );
        group.setAttribute( BG_EDIT_TYPE_ATTR, editType );
        group.setAttribute( BG_LAYER_ATTR, layer );

        /* Clone template content (paths, rects) into the new group. */
        var children = templateElement.childNodes;
        for ( var i = 0; i < children.length; i++ ) {
            if ( children[i].nodeType === 1 ) {
                group.appendChild( children[i].cloneNode( true ) );
            }
        }

        if ( editType === 'icon' ) {
            /* Icon: position via transform. */
            group.setAttribute( 'transform',
                'scale(1 1) translate(' + svgPoint.x + ',' + svgPoint.y + ') rotate(0, 0, 0)' );

            /* Add hit-area rect from bounding box of template content. */
            var bbox = getTemplateBBox( templateElement );
            var hitRect = document.createElementNS( SVG_NS, 'rect' );
            hitRect.setAttribute( 'x', bbox.x );
            hitRect.setAttribute( 'y', bbox.y );
            hitRect.setAttribute( 'width', bbox.width );
            hitRect.setAttribute( 'height', bbox.height );
            hitRect.setAttribute( 'fill', 'transparent' );
            hitRect.setAttribute( 'class', BG_HIT_AREA_CLASS );
            group.appendChild( hitRect );

        } else if ( editType === 'open' ) {
            /* Open path: offset the template path to the drop point. */
            var path = group.querySelector( 'path' );
            if ( path ) {
                var offsetD = offsetPathData( path.getAttribute( 'd' ), svgPoint.x, svgPoint.y );
                path.setAttribute( 'd', offsetD );

                /* Add hit-area path with same data. */
                var hitPath = document.createElementNS( SVG_NS, 'path' );
                hitPath.setAttribute( 'd', offsetD );
                hitPath.setAttribute( 'class', BG_HIT_AREA_CLASS );
                group.appendChild( hitPath );
            }

        } else if ( editType === 'closed' ) {
            /* Closed path: offset the template path to the drop point. */
            var path = group.querySelector( 'path' );
            if ( path ) {
                var offsetD = offsetPathData( path.getAttribute( 'd' ), svgPoint.x, svgPoint.y );
                path.setAttribute( 'd', offsetD );
            }
        }

        return group;
    }

    function offsetPathData( d, offsetX, offsetY ) {
        /* Offset all coordinates in an M/L/Z path by the given amounts. */
        return d.replace( /([\d.]+),([\d.]+)/g, function( match, x, y ) {
            var newX = parseFloat( x ) + offsetX;
            var newY = parseFloat( y ) + offsetY;
            return newX.toFixed(1) + ',' + newY.toFixed(1);
        });
    }

    function getTemplateBBox( templateElement ) {
        /* Parse path coordinates to compute bounding box. */
        var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        var paths = templateElement.querySelectorAll( 'path' );
        for ( var i = 0; i < paths.length; i++ ) {
            var coords = paths[i].getAttribute( 'd' ).match( /[\d.]+/g );
            if ( ! coords ) { continue; }
            for ( var j = 0; j < coords.length; j += 2 ) {
                var x = parseFloat( coords[j] );
                var y = parseFloat( coords[j + 1] );
                if ( ! isNaN( x ) && ! isNaN( y ) ) {
                    if ( x < minX ) { minX = x; }
                    if ( y < minY ) { minY = y; }
                    if ( x > maxX ) { maxX = x; }
                    if ( y > maxY ) { maxY = y; }
                }
            }
        }
        if ( minX === Infinity ) { return { x: 0, y: 0, width: 50, height: 50 }; }
        return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
    }

    function insertAtLayer( canvasSvg, newElement, layer ) {
        /* Insert the element at the correct position based on layer ordering.
           Elements with higher layer numbers come later in the DOM (render on top). */
        var editorGroup = canvasSvg.querySelector( 'g[' + BG_EDITOR_ATTR + ']' );
        if ( ! editorGroup ) { return; }

        var elements = editorGroup.querySelectorAll( 'g.' + BG_ELEMENT_CLASS );
        var insertBefore = null;
        for ( var i = 0; i < elements.length; i++ ) {
            var elemLayer = parseInt( elements[i].getAttribute( BG_LAYER_ATTR ) || '0', 10 );
            if ( elemLayer > layer ) {
                insertBefore = elements[i];
                break;
            }
        }

        if ( insertBefore ) {
            editorGroup.insertBefore( newElement, insertBefore );
        } else {
            editorGroup.appendChild( newElement );
        }
    }

    /* ==================== */
    /* Core Initialization  */
    /* ==================== */

    function initCores() {
        Hi.SvgPanZoomCore.init({
            baseSvgSelector: '#' + CANVAS_SVG_ID,
            areaSelector: '#' + CANVAS_AREA_ID,
            onSave: null,
            shouldSave: function() { return false; },
        });

        Hi.SvgIconCore.init({
            identifyElement: function( event ) {
                var target = event.target || event.srcElement;
                var group = $( target ).closest( 'g.' + BG_ELEMENT_CLASS );
                if ( group.length > 0 && group.attr( BG_EDIT_TYPE_ATTR ) === 'icon' ) {
                    return group[0];
                }
                return null;
            },
            onSelect: function( element ) {
                Hi.SvgPathCore.clearSelection();
            },
            onDeselect: function() {
                /* Future: clear element info in editor UI */
            },
            onSave: function( element, positionData ) {
                saveDraft();
            },
            baseSvgSelector: '#' + CANVAS_SVG_ID,
            areaSelector: '#' + CANVAS_AREA_ID,
            highlightClass: Hi.HIGHLIGHTED_CLASS,
        });

        Hi.SvgPathCore.init({
            identifyElement: function( event ) {
                var target = event.target || event.srcElement;
                var group = $( target ).closest( 'g.' + BG_ELEMENT_CLASS );
                if ( group.length > 0 ) {
                    var editType = group.attr( BG_EDIT_TYPE_ATTR );
                    if ( editType === 'open' || editType === 'closed' ) {
                        return group[0];
                    }
                }
                return null;
            },
            onSelect: function( element ) {
                Hi.SvgIconCore.clearSelection();
            },
            onDeselect: function() {
                saveDraft();
            },
            onSave: function( element, svgPathString ) {
                /* Update the hidden path element's d attribute so
                   saveDraft() serializes the current geometry. */
                $( element ).find( 'path' ).not( '.hi-bg-hit-area' ).attr( 'd', svgPathString );
                $( element ).find( 'path.hi-bg-hit-area' ).attr( 'd', svgPathString );
                saveDraft();
            },
            allowDeleteAll: true,
            onDeleteAll: function() {
                Hi.SvgEdit.onElementDeleted();
            },
            baseSvgSelector: '#' + CANVAS_SVG_ID,
            highlightClass: Hi.HIGHLIGHTED_CLASS,
        });
    }

    /* ==================== */
    /* Conformance Check    */
    /* ==================== */

    function checkConformance() {
        var canvasSvg = document.getElementById( CANVAS_SVG_ID );
        if ( ! canvasSvg ) { return; }

        var baseGroup = canvasSvg.querySelector( Hi.LOCATION_VIEW_BASE_SELECTOR );
        if ( ! baseGroup ) { return; }

        var editorGroup = baseGroup.querySelector( 'g[' + BG_EDITOR_ATTR + ']' );
        if ( ! editorGroup ) {
            /* Wrap existing content in an editor group so palette items can be added. */
            editorGroup = document.createElementNS( 'http://www.w3.org/2000/svg', 'g' );
            editorGroup.setAttribute( BG_EDITOR_ATTR, '1' );
            while ( baseGroup.firstChild ) {
                editorGroup.appendChild( baseGroup.firstChild );
            }
            baseGroup.appendChild( editorGroup );

            showConformanceWarning();
            return;
        }

        /* Count direct child elements of the editor group (excluding defs). */
        var children = editorGroup.children;
        var totalElements = 0;
        var editableElements = 0;
        for ( var i = 0; i < children.length; i++ ) {
            var child = children[i];
            if ( child.tagName === 'defs' ) { continue; }
            totalElements++;
            if ( child.classList && child.classList.contains( BG_ELEMENT_CLASS )
                 && child.getAttribute( BG_EDIT_TYPE_ATTR ) ) {
                editableElements++;
            }
        }

        if ( totalElements > 0 && editableElements < totalElements ) {
            showConformanceWarning();
        }
    }

    function showConformanceWarning() {
        $( '#' + CONFORMANCE_WARNING_ID ).show();
    }

    function refreshAfterAsyncRender() {
        Hi.SvgPanZoomCore.refresh();
    }

    $(document).ready(function() {
        buildPalette();
        initPaletteDrop();
        initCores();
        checkConformance();
        AN.addAfterAsyncRenderFunction( refreshAfterAsyncRender );

        /* Seed undo cache so the first edit has a valid pre-edit state. */
        gLastSavedSnapshot = getCleanSnapshot();

        $( '#hi-svg-edit-snap-grid' ).on( 'change input', function() {
            Hi.SvgEdit.snapGridPixels = parseInt( $( this ).val(), 10 ) || 0;
        });
    });

})();
