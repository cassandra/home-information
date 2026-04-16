/* Location SVG Editor Javascript */

(function() {

    window.Hi = window.Hi || {};
    window.Hi.SvgEdit = window.Hi.SvgEdit || {};

    const SVG_NS = 'http://www.w3.org/2000/svg';
    const PALETTE_CONTAINER_ID = 'hi-svg-edit-palette';
    const CANVAS_SVG_ID = 'hi-svg-edit-svg';

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

        var editorGroup = canvasSvg.querySelector('g[data-hi-editor]');
        if (!editorGroup) {
            return;
        }
        var defsElement = editorGroup.querySelector('defs');
        if (!defsElement) {
            return;
        }

        var templates = [];
        $(defsElement).children('g').each(function() {
            var editType = $(this).attr('data-bg-edit-type');
            if (!editType) {
                return;
            }
            templates.push({
                id: $(this).attr('id'),
                editType: editType,
                label: $(this).attr('data-bg-label') || '',
                category: $(this).attr('data-bg-category') || '',
                layer: parseInt($(this).attr('data-bg-layer') || '0', 10),
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
            catDiv.className = 'hi-palette-category';

            var catLabel = document.createElement('span');
            catLabel.className = 'hi-palette-category-label';
            catLabel.textContent = CATEGORY_LABELS[catKey] || catKey;
            catDiv.appendChild(catLabel);

            var itemsDiv = document.createElement('div');
            itemsDiv.className = 'hi-palette-items';

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
        itemDiv.className = 'hi-palette-item';
        itemDiv.setAttribute('data-bg-template-id', tmpl.id);
        itemDiv.setAttribute('title', tmpl.label);

        var swatchSvg = createSwatchSvg(tmpl);
        itemDiv.appendChild(swatchSvg);

        var label = document.createElement('span');
        label.className = 'hi-palette-label';
        label.textContent = tmpl.label;
        itemDiv.appendChild(label);

        return itemDiv;
    }

    function createSwatchSvg(tmpl) {
        var svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('class', 'hi-palette-swatch');
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
    /* Draft Save           */
    /* ==================== */

    var PROXY_PATH_CONTAINER_ID = 'hi-proxy-path-container';

    function saveDraft() {
        var canvasSvg = document.getElementById( CANVAS_SVG_ID );
        if ( ! canvasSvg ) { return; }

        var editorGroup = canvasSvg.querySelector( 'g[data-hi-editor]' );
        if ( ! editorGroup ) { return; }

        /* Temporarily remove proxy editing elements before serializing. */
        var proxyContainer = document.getElementById( PROXY_PATH_CONTAINER_ID );
        var proxyParent = null;
        if ( proxyContainer ) {
            proxyParent = proxyContainer.parentNode;
            proxyParent.removeChild( proxyContainer );
        }

        var svgContent = editorGroup.outerHTML;

        /* Restore proxy elements. */
        if ( proxyContainer && proxyParent ) {
            proxyParent.appendChild( proxyContainer );
        }

        if ( ! Hi.SvgEdit.saveUrl ) { return; }

        $.post( Hi.SvgEdit.saveUrl, {
            svg_content: svgContent,
            csrfmiddlewaretoken: Hi.SvgEdit.csrfToken,
        });
    }

    /* ==================== */
    /* Core Initialization  */
    /* ==================== */

    function initCores() {
        Hi.SvgPanZoomCore.init({
            baseSvgSelector: '#' + CANVAS_SVG_ID,
            areaSelector: '#hi-svg-edit-canvas',
            onSave: null,
            shouldSave: function() { return false; },
        });

        Hi.SvgIconCore.init({
            identifyElement: function( event ) {
                var target = event.target || event.srcElement;
                var group = $( target ).closest( 'g.hi-bg-element' );
                if ( group.length > 0 && group.attr( 'data-bg-edit-type' ) === 'icon' ) {
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
            areaSelector: '#hi-svg-edit-canvas',
            highlightClass: 'highlighted',
        });

        Hi.SvgPathCore.init({
            identifyElement: function( event ) {
                var target = event.target || event.srcElement;
                var group = $( target ).closest( 'g.hi-bg-element' );
                if ( group.length > 0 ) {
                    var editType = group.attr( 'data-bg-edit-type' );
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
            onSave: null,
            baseSvgSelector: '#' + CANVAS_SVG_ID,
            highlightClass: 'highlighted',
        });
    }

    $(document).ready(function() {
        buildPalette();
        initCores();
    });

})();
