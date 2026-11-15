/*
 * Home Information - Attribute Unsaved-Changes Guard
 *
 * Stops actions that would throw away unsaved edits in a modal's
 * attribute editor. Instead, the modal's unsaved-changes banner is
 * shown: DISCARD CHANGES proceeds with the held action; KEEP EDITING
 * cancels it. The banner also goes away on its own once nothing is
 * unsaved (e.g., after a save or a content re-render).
 *
 * A modal opts in by including the banner partial
 * (attribute/components/unsaved_changes_banner.html).
 *
 * Actions covered:
 *  - Bootstrap closes (X, Esc, backdrop): vetoed at hide.bs.modal.
 *  - antinode data-async links that would close the modal (e.g.
 *    STATUS / HISTORY), and attribute restore links, which re-render
 *    the editor from the server. Both are caught in the document
 *    capture phase, before their own handlers act.
 *
 * Closes that follow a save (DONE) pass because the save clears the
 * dirty state first.
 */

(function() {
    'use strict';

    const GUARD_INTERNAL = {
        MODAL_SELECTOR: '.modal',
        HIDDEN_CLASS: 'd-none',
        // Mirrors antinode: these elements close their modal unless
        // marked data-stay-in-modal.
        ASYNC_EXIT_SELECTOR: 'a[data-async], div[data-async]',
        STAY_IN_MODAL_ATTR: 'data-stay-in-modal',
        PENDING_ACTION_DATA_KEY: 'attr-v2-pending-action',
    };

    window.Hi = window.Hi || {};
    window.Hi.attr = window.Hi.attr || {};

    function _bannerOf($modal) {
        return $modal.find(Hi.ATTR_V2_UNSAVED_BANNER_SELECTOR).first();
    }

    function _editorContainerIdOf($modal) {
        return $modal.find(Hi.ATTR_V2_CONTAINER_SELECTOR).first().attr('id');
    }

    function _hasUnsavedChanges($modal) {
        if (_bannerOf($modal).length === 0) return false;
        const containerId = _editorContainerIdOf($modal);
        return Boolean(containerId) && Hi.attr.dirtyTracking.isDirty(containerId);
    }

    function _holdAction($modal, resumeAction) {
        const $banner = _bannerOf($modal);
        $banner.data(GUARD_INTERNAL.PENDING_ACTION_DATA_KEY, resumeAction);
        $banner.removeClass(GUARD_INTERNAL.HIDDEN_CLASS);
        // Focusing also scrolls the banner into view.
        $banner.find(Hi.ATTR_V2_KEEP_EDITING_BTN_SELECTOR).trigger('focus');
    }

    function _releaseBanner($banner) {
        const resumeAction = $banner.data(GUARD_INTERNAL.PENDING_ACTION_DATA_KEY);
        $banner.removeData(GUARD_INTERNAL.PENDING_ACTION_DATA_KEY);
        $banner.addClass(GUARD_INTERNAL.HIDDEN_CLASS);
        return resumeAction;
    }

    function _discardChanges($banner) {
        const $modal = $banner.closest(GUARD_INTERNAL.MODAL_SELECTOR);
        const resumeAction = _releaseBanner($banner);
        Hi.attr.dirtyTracking.clearDirtyState(_editorContainerIdOf($modal));
        if (resumeAction) resumeAction();
    }

    function _keepEditing($banner) {
        _releaseBanner($banner);
    }

    $(document).on('hide.bs.modal', GUARD_INTERNAL.MODAL_SELECTOR, function(e) {
        if (e.target !== this) return;
        const $modal = $(this);
        if (!_hasUnsavedChanges($modal)) return;

        e.preventDefault();
        _holdAction($modal, () => $modal.modal('hide'));
    });

    function _editDiscardingElementOf(target) {
        const restoreLink = target.closest(Hi.ATTR_V2_RESTORE_LINK_SELECTOR);
        if (restoreLink) return restoreLink;

        const asyncExit = target.closest(GUARD_INTERNAL.ASYNC_EXIT_SELECTOR);
        if (asyncExit && !asyncExit.hasAttribute(GUARD_INTERNAL.STAY_IN_MODAL_ATTR)) {
            return asyncExit;
        }
        return null;
    }

    document.addEventListener('click', function(e) {
        const actionElement = _editDiscardingElementOf(e.target);
        if (!actionElement) return;

        const $modal = $(actionElement).closest(GUARD_INTERNAL.MODAL_SELECTOR);
        if ($modal.length === 0 || !_hasUnsavedChanges($modal)) return;

        e.preventDefault();
        e.stopPropagation();
        _holdAction($modal, () => actionElement.click());
    }, true);

    $(document).on(Hi.ATTR_V2_DIRTY_STATE_CHANGED_EVENT, Hi.ATTR_V2_CONTAINER_SELECTOR, function(e, isDirty) {
        if (isDirty) return;
        const $banner = _bannerOf($(this).closest(GUARD_INTERNAL.MODAL_SELECTOR));
        if ($banner.length > 0) _releaseBanner($banner);
    });

    $(document).on('click', Hi.ATTR_V2_DISCARD_CHANGES_BTN_SELECTOR, function() {
        _discardChanges($(this).closest(Hi.ATTR_V2_UNSAVED_BANNER_SELECTOR));
    });

    $(document).on('click', Hi.ATTR_V2_KEEP_EDITING_BTN_SELECTOR, function() {
        _keepEditing($(this).closest(Hi.ATTR_V2_UNSAVED_BANNER_SELECTOR));
    });

})();
