/*
 * Home Information - External-reference card actions
 *
 * Per-card rename / unlink / reorder for the framework-rendered
 * external-reference grid on Entity / Location edit modals. Each
 * action posts to its own endpoint and swaps the grid HTML in
 * place via antinode's replace-map -- the surrounding modal stays
 * open.
 *
 * Handlers are delegated at the document level so antinode-loaded
 * modal content wires up automatically -- no per-modal init step.
 * Mirrors the attr-picker.js shape; CSS reuse is via the existing
 * ``attr-v2-file-*`` classes on the card template itself.
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

    function _postAction(url, fields) {
        // Use the antinode AJAX entry point so the response's
        // replace-map is applied to the page. Falls back to a plain
        // jQuery post if antinode is missing (defensive only;
        // antinode is in the base bundle).
        const payload = Object.assign({ csrfmiddlewaretoken: _csrfToken() }, fields);
        if (window.AN) {
            window.AN.post(url, $.param(payload));
            return;
        }
        $.post(url, payload);
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

})();
