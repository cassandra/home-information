/*
 * Home Information - External-reference card actions
 *
 * Per-card rename / unlink / reorder for the framework-rendered
 * external-reference grid on Entity / Location edit modals. Each
 * action POSTs to its own endpoint; the response is the freshly-
 * rendered grid HTML, which replaces the existing grid in place so
 * the surrounding modal stays open.
 *
 * The action endpoints already require custom JS (we extract the
 * reference id from the card, fire on input blur for rename, etc.),
 * so antinode's declarative wiring doesn't pull weight here -- we
 * just $.ajax + replaceWith directly. The grid is located by
 * closest() traversal from the clicked card, so no template ->
 * JS magic-string id agreement is required.
 *
 * Handlers are delegated at the document level so dynamically-
 * inserted modal content wires up automatically -- no per-modal
 * init step. CSS reuse is via the existing ``attr-v2-file-*``
 * classes on the card template itself.
 *
 * DOM classes, data attributes, and JSON field names come from
 * ``Hi.EXT_REF_*`` in main.js, mirrored server-side in
 * ``hi.constants.DIVID``.
 */
(function() {
    'use strict';

    const EventNs = '.ext-ref';

    function _classSelector(className) {
        return '.' + className;
    }

    function _csrfToken() {
        const name = 'csrftoken';
        const cookies = document.cookie ? document.cookie.split(';') : [];
        for (let i = 0; i < cookies.length; i++) {
            const c = cookies[i].trim();
            if (c.substring(0, name.length + 1) === (name + '=')) {
                return decodeURIComponent(c.substring(name.length + 1));
            }
        }
        return '';
    }

    function _cardContext($card) {
        return {
            referenceId: $card.attr(Hi.EXT_REF_REFERENCE_ID_ATTR),
            ownerType:   $card.attr(Hi.EXT_REF_OWNER_TYPE_ATTR),
        };
    }

    function _postAction(url, fields, $card) {
        // The grid is the card's nearest ancestor with the grid
        // class -- no id agreement between JS and template needed.
        const $grid = $card.closest(_classSelector(Hi.EXT_REF_GRID_CLASS));
        const payload = Object.assign({ csrfmiddlewaretoken: _csrfToken() }, fields);
        // No .fail() handler: server-side BadRequest / 404 responses
        // are dropped client-side and the grid simply doesn't
        // refresh. The server logs the error; the operator can
        // retry or refresh the modal.
        $.ajax({
            url: url,
            method: 'POST',
            data: payload,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        }).done(function(html) {
            $grid.replaceWith(html);
        });
    }

    function _actionUrl(viewName, ownerType, referenceId) {
        // Template-rendered Django URLs aren't available client-side
        // for arbitrary view names, so the path is composed by
        // convention. Keep this in sync with ``hi.integrations.urls``.
        return '/integration/external-references/'
            + encodeURIComponent(ownerType)
            + '/' + encodeURIComponent(referenceId)
            + '/' + viewName + '/';
    }

    // ---- Title rename: commit on blur or Enter --------------------

    $(document).on(
        'change' + EventNs + ' blur' + EventNs,
        _classSelector(Hi.EXT_REF_TITLE_INPUT_CLASS),
        function() {
            const $input = $(this);
            const $card = $input.closest(_classSelector(Hi.EXT_REF_CARD_CLASS));
            if ($card.length === 0) return;
            const newTitle = ($input.val() || '').trim();
            if (!newTitle) {
                // Restore the previous value rather than POST an
                // empty title (the server would 400). Use the input's
                // last-good defaultValue if present.
                $input.val($input.prop('defaultValue'));
                return;
            }
            if (newTitle === $input.prop('defaultValue')) {
                // No-op when the value hasn't actually changed
                // (blur fires even on a no-edit visit).
                return;
            }
            const ctx = _cardContext($card);
            const fields = {};
            fields[Hi.EXT_REF_TITLE_FIELD] = newTitle;
            _postAction(
                _actionUrl('rename', ctx.ownerType, ctx.referenceId),
                fields,
                $card,
            );
        }
    );

    $(document).on(
        'keydown' + EventNs,
        _classSelector(Hi.EXT_REF_TITLE_INPUT_CLASS),
        function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                $(this).blur();
            }
        }
    );

    // ---- Unlink (delete) ---------------------------------------

    $(document).on(
        'click' + EventNs,
        _classSelector(Hi.EXT_REF_DELETE_BTN_CLASS),
        function(e) {
            e.preventDefault();
            const $card = $(this).closest(_classSelector(Hi.EXT_REF_CARD_CLASS));
            if ($card.length === 0) return;
            const ctx = _cardContext($card);
            _postAction(
                _actionUrl('delete', ctx.ownerType, ctx.referenceId),
                {},
                $card,
            );
        }
    );

    // ---- Reorder (move left / right) ---------------------------

    function _reorder(e, direction) {
        e.preventDefault();
        const $card = $(this).closest(_classSelector(Hi.EXT_REF_CARD_CLASS));
        if ($card.length === 0) return;
        const ctx = _cardContext($card);
        const fields = {};
        fields[Hi.EXT_REF_DIRECTION_FIELD] = direction;
        _postAction(
            _actionUrl('reorder', ctx.ownerType, ctx.referenceId),
            fields,
            $card,
        );
    }

    $(document).on(
        'click' + EventNs,
        _classSelector(Hi.EXT_REF_REORDER_LEFT_CLASS),
        function(e) { _reorder.call(this, e, Hi.EXT_REF_DIRECTION_LEFT); }
    );
    $(document).on(
        'click' + EventNs,
        _classSelector(Hi.EXT_REF_REORDER_RIGHT_CLASS),
        function(e) { _reorder.call(this, e, Hi.EXT_REF_DIRECTION_RIGHT); }
    );

    // ---- Open upstream (thumbnail click) -----------------------

    // The thumbnail click is wired here (rather than inline on the
    // template) because ``source_url`` is upstream-supplied; an
    // inline ``onclick="window.open('{{ url }}', ...)"`` lets a
    // crafted URL break out of the JS string literal even after
    // Django's attribute escaping. Reading the URL via .attr()
    // round-trips safely.
    $(document).on(
        'click' + EventNs,
        '[' + Hi.EXT_REF_SOURCE_URL_ATTR + ']',
        function() {
            const url = $(this).attr(Hi.EXT_REF_SOURCE_URL_ATTR);
            if (url) window.open(url, '_blank', 'noopener');
        }
    );

})();
