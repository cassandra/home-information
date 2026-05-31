/*
 * Home Information - External-reference picker UI state
 *
 * Multi-select picker for EXTERNAL_REFERENCE integrations (e.g.,
 * paperless-ngx). The picker lets the operator search an upstream
 * source and accumulate a set of references (title + URL) across
 * multiple searches, then commit the whole set as TEXT attributes
 * in one final submit.
 *
 * Responsibilities owned by this module:
 *
 *   - Hold the current attribute-selection set in JS state, keyed
 *     by picker-DOM-node so multiple modals would not collide.
 *   - Render the chip row from that state. Chips are the only HTML
 *     this module generates; everything else is server-rendered.
 *   - Update the Add button's label and enabled state to reflect
 *     the current selection count.
 *   - Drive an async Search request: POST query parameters, receive
 *     result-cards HTML, swap into the results container. After
 *     swap, re-apply checkbox state to any newly-visible result
 *     whose URL is already in the selection set.
 *   - On Add submit: serialize the selection set into the hidden
 *     ``selections_json`` input and POST through antinode's public
 *     API (``AN.hideModalIfNeeded`` + ``AN.post``) so the modal
 *     close and the ``{refresh: true}`` response flow through the
 *     framework.
 *
 * Handlers are delegated at the document level so dynamically-
 * inserted modal content (the antinode-loaded picker body) wires
 * up automatically — no per-modal init step. State is lazily
 * created per picker DOM node and garbage-collected when the
 * modal is removed.
 *
 * DOM classes, data-attribute names, and wire-format field names
 * all come from ``Hi.REF_PICKER_*`` in ``main.js``, mirrored
 * server-side in ``hi.constants.DIVID``.
 */
(function() {
    'use strict';

    const EventNs = '.external-reference-picker';

    // Per-picker selection state, keyed by the picker-root DOM node
    // so multiple open modals would not collide. State is lazily
    // created on first access and garbage-collected when the modal
    // element is removed.
    const _stateByPicker = new WeakMap();

    function _state(pickerRoot) {
        let state = _stateByPicker.get(pickerRoot);
        if (!state) {
            state = { attrSelections: [] };
            _stateByPicker.set(pickerRoot, state);
        }
        return state;
    }

    function _classSelector(className) {
        return '.' + className;
    }

    function _hasSelection(state, sourceUrl) {
        const key = Hi.REF_PICKER_SELECTION_URL_KEY;
        return state.attrSelections.some(s => s[key] === sourceUrl);
    }

    function _addSelection(state, fields) {
        if (_hasSelection(state, fields.sourceUrl)) return;
        const record = {};
        record[Hi.REF_PICKER_SELECTION_TITLE_KEY] = fields.title;
        record[Hi.REF_PICKER_SELECTION_URL_KEY] = fields.sourceUrl;
        record[Hi.REF_PICKER_SELECTION_INTEGRATION_NAME_KEY] = fields.integrationName;
        record[Hi.REF_PICKER_SELECTION_MIME_TYPE_KEY] = fields.mimeType || '';
        state.attrSelections.push(record);
    }

    function _removeSelection(state, sourceUrl) {
        const key = Hi.REF_PICKER_SELECTION_URL_KEY;
        state.attrSelections = state.attrSelections.filter(
            s => s[key] !== sourceUrl
        );
    }

    function _renderChips($pickerRoot, state) {
        const $chipsContainer = $pickerRoot.find(
            _classSelector(Hi.REF_PICKER_CHIPS_CLASS)
        );
        const $emptyHint = $pickerRoot.find(
            _classSelector(Hi.REF_PICKER_CHIPS_EMPTY_CLASS)
        );
        $chipsContainer.empty();
        if (state.attrSelections.length === 0) {
            $emptyHint.removeClass('d-none');
            return;
        }
        $emptyHint.addClass('d-none');
        const titleKey = Hi.REF_PICKER_SELECTION_TITLE_KEY;
        const urlKey = Hi.REF_PICKER_SELECTION_URL_KEY;
        state.attrSelections.forEach(function(sel) {
            const $chip = $('<span>')
                .addClass('badge badge-secondary mr-2 mb-2 d-inline-flex align-items-center');
            $('<span>')
                .addClass('mr-1 text-truncate')
                .css('max-width', '220px')
                .attr('title', sel[titleKey])
                .text(sel[titleKey])
                .appendTo($chip);
            $('<button type="button">')
                .addClass('btn btn-link btn-sm p-0 text-white ml-1')
                .addClass(Hi.REF_PICKER_CHIP_REMOVE_CLASS)
                .attr('title', 'Remove from selection')
                .attr(Hi.REF_PICKER_SOURCE_URL_ATTR, sel[urlKey])
                .text('×')   // ×
                .appendTo($chip);
            $chipsContainer.append($chip);
        });
    }

    function _renderAttachButton($pickerRoot, state) {
        const count = state.attrSelections.length;
        const $btn = $pickerRoot.find(
            _classSelector(Hi.REF_PICKER_ATTACH_BTN_CLASS)
        );
        const noun = count === 1 ? 'Link' : 'Links';
        const $label = $btn.find(
            _classSelector(Hi.REF_PICKER_ATTACH_LABEL_CLASS)
        );
        const text = 'Add ' + count + ' ' + noun;
        if ($label.length) {
            $label.text(text);
        } else {
            $btn.text(text);
        }
        $btn.prop('disabled', count === 0);
    }

    function _renderAll($pickerRoot, state) {
        _renderChips($pickerRoot, state);
        _renderAttachButton($pickerRoot, state);
    }

    function _syncCheckboxesToState($pickerRoot, state) {
        $pickerRoot.find(
            _classSelector(Hi.REF_PICKER_RESULT_CHECKBOX_CLASS)
        ).each(function() {
            const $cb = $(this);
            const sourceUrl = $cb.attr(Hi.REF_PICKER_SOURCE_URL_ATTR);
            if (sourceUrl == null) return;
            $cb.prop('checked', _hasSelection(state, sourceUrl));
        });
    }

    // ---- Delegated handlers ------------------------------------

    $(document).on(
        'change' + EventNs,
        _classSelector(Hi.REF_PICKER_RESULT_CHECKBOX_CLASS),
        function() {
            const $cb = $(this);
            const $pickerRoot = $cb.closest(
                _classSelector(Hi.REF_PICKER_ROOT_CLASS)
            );
            if ($pickerRoot.length === 0) return;
            const state = _state($pickerRoot[0]);
            const sourceUrl = $cb.attr(Hi.REF_PICKER_SOURCE_URL_ATTR);
            if (sourceUrl == null) return;
            if ($cb.is(':checked')) {
                _addSelection(state, {
                    title:           $cb.attr(Hi.REF_PICKER_TITLE_ATTR),
                    sourceUrl:       sourceUrl,
                    integrationName: $cb.attr(Hi.REF_PICKER_INTEGRATION_NAME_ATTR),
                    mimeType:        $cb.attr(Hi.REF_PICKER_MIME_TYPE_ATTR),
                });
            } else {
                _removeSelection(state, sourceUrl);
            }
            _renderAll($pickerRoot, state);
        }
    );

    $(document).on(
        'click' + EventNs,
        _classSelector(Hi.REF_PICKER_CHIP_REMOVE_CLASS),
        function() {
            const $btn = $(this);
            const $pickerRoot = $btn.closest(
                _classSelector(Hi.REF_PICKER_ROOT_CLASS)
            );
            if ($pickerRoot.length === 0) return;
            const sourceUrl = $btn.attr(Hi.REF_PICKER_SOURCE_URL_ATTR);
            if (sourceUrl == null) return;
            const state = _state($pickerRoot[0]);
            _removeSelection(state, sourceUrl);
            // Uncheck any visible result card whose URL matches.
            $pickerRoot
                .find(_classSelector(Hi.REF_PICKER_RESULT_CHECKBOX_CLASS))
                .filter(function() {
                    return $(this).attr(Hi.REF_PICKER_SOURCE_URL_ATTR) === sourceUrl;
                })
                .prop('checked', false);
            _renderAll($pickerRoot, state);
        }
    );

    $(document).on(
        'submit' + EventNs,
        _classSelector(Hi.REF_PICKER_SEARCH_FORM_CLASS),
        function(e) {
            e.preventDefault();
            const $form = $(this);
            const $pickerRoot = $form.closest(
                _classSelector(Hi.REF_PICKER_ROOT_CLASS)
            );
            if ($pickerRoot.length === 0) return;
            const searchUrl = $form.attr(Hi.REF_PICKER_SEARCH_URL_ATTR);
            $.ajax({
                url: searchUrl,
                method: 'POST',
                data: $form.serialize(),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            }).done(function(html) {
                $pickerRoot.find(
                    _classSelector(Hi.REF_PICKER_RESULTS_CLASS)
                ).html(html);
                _syncCheckboxesToState($pickerRoot, _state($pickerRoot[0]));
            });
        }
    );

    $(document).on(
        'submit' + EventNs,
        _classSelector(Hi.REF_PICKER_ATTACH_FORM_CLASS),
        function(e) {
            // Own the submit lifecycle so the in-memory selection set
            // is populated into the hidden input BEFORE the form is
            // read. The form deliberately omits ``data-async`` so
            // antinode's body-level submit handler doesn't race us —
            // we instead route through antinode's public API (modal
            // close + POST) so the ``{refresh: true}`` response and
            // the modal cleanup still flow through the framework.
            e.preventDefault();
            const $form = $(this);
            const $pickerRoot = $form.closest(
                _classSelector(Hi.REF_PICKER_ROOT_CLASS)
            );
            if ($pickerRoot.length === 0) return;
            const state = _state($pickerRoot[0]);
            const fieldName = Hi.REF_PICKER_SELECTIONS_JSON_FIELD;
            $form.find('input[name="' + fieldName + '"]')
                .val(JSON.stringify(state.attrSelections));
            if (!window.AN) {
                // Defensive: antinode is part of the base bundle, but
                // if it ever fails to load we fall back to a plain
                // submit so the operator's click is not lost.
                $form[0].submit();
                return;
            }
            window.AN.hideModalIfNeeded($form[0]);
            window.AN.post($form.attr('action'), $form.serialize());
        }
    );

    $(document).on(
        'click' + EventNs,
        _classSelector(Hi.REF_PICKER_SOURCE_OPTION_CLASS),
        function(e) {
            // Switch the active source. Selections are CLEARED --
            // each submission carries items from one integration
            // only, matching the typical "pick from this source"
            // workflow. Operators who want a mix submit one batch
            // per source.
            e.preventDefault();
            const $option = $(this);
            const $pickerRoot = $option.closest(
                _classSelector(Hi.REF_PICKER_ROOT_CLASS)
            );
            if ($pickerRoot.length === 0) return;
            const sourceId = $option.attr(Hi.REF_PICKER_SOURCE_ID_ATTR);
            const sourceLogo = $option.attr(Hi.REF_PICKER_SOURCE_LOGO_ATTR);
            const sourceLabel = $option.attr(Hi.REF_PICKER_SOURCE_LABEL_ATTR);
            if (sourceId == null) return;
            const state = _state($pickerRoot[0]);
            state.attrSelections = [];
            _renderAll($pickerRoot, state);
            $pickerRoot
                .find(_classSelector(Hi.REF_PICKER_SOURCE_BANNER_LOGO_CLASS))
                .attr('src', sourceLogo);
            $pickerRoot
                .find(_classSelector(Hi.REF_PICKER_SOURCE_BANNER_LABEL_CLASS))
                .text(sourceLabel);
            const fieldName = Hi.REF_PICKER_INTEGRATION_ID_FIELD;
            $pickerRoot
                .find('input[name="' + fieldName + '"]')
                .val(sourceId);
            $pickerRoot
                .find(_classSelector(Hi.REF_PICKER_SEARCH_FORM_CLASS))
                .trigger('submit');
        }
    );

})();
