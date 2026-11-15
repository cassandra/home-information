/*
 * Home Information - Attribute Unsaved-Changes Guard
 *
 * Stops a modal containing an attribute editor from being left while
 * it has unsaved edits. Instead of exiting, the modal's unsaved-changes
 * banner is shown: DISCARD CHANGES proceeds with the original exit;
 * KEEP EDITING stays put.
 *
 * A modal opts in by including the banner partial
 * (attribute/components/unsaved_changes_banner.html).
 *
 * Exits covered:
 *  - Bootstrap closes (X, Esc, backdrop): vetoed at hide.bs.modal.
 *  - antinode data-async links that would close the modal (e.g.
 *    STATUS / HISTORY). These must be stopped before antinode's
 *    body-level handler hides the modal and starts the fetch, so they
 *    are caught in the document capture phase.
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
        PENDING_EXIT_DATA_KEY: 'attr-v2-pending-exit',
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

    function _holdExit($modal, resumeExit) {
        const $banner = _bannerOf($modal);
        $banner.data(GUARD_INTERNAL.PENDING_EXIT_DATA_KEY, resumeExit);
        $banner.removeClass(GUARD_INTERNAL.HIDDEN_CLASS);
        // Focusing also scrolls the banner into view.
        $banner.find(Hi.ATTR_V2_KEEP_EDITING_BTN_SELECTOR).trigger('focus');
    }

    function _releaseBanner($banner) {
        const resumeExit = $banner.data(GUARD_INTERNAL.PENDING_EXIT_DATA_KEY);
        $banner.removeData(GUARD_INTERNAL.PENDING_EXIT_DATA_KEY);
        $banner.addClass(GUARD_INTERNAL.HIDDEN_CLASS);
        return resumeExit;
    }

    function _discardChanges($banner) {
        const $modal = $banner.closest(GUARD_INTERNAL.MODAL_SELECTOR);
        const resumeExit = _releaseBanner($banner);
        Hi.attr.dirtyTracking.clearDirtyState(_editorContainerIdOf($modal));
        if (resumeExit) resumeExit();
    }

    function _keepEditing($banner) {
        _releaseBanner($banner);
    }

    $(document).on('hide.bs.modal', GUARD_INTERNAL.MODAL_SELECTOR, function(e) {
        if (e.target !== this) return;
        const $modal = $(this);
        if (!_hasUnsavedChanges($modal)) return;

        e.preventDefault();
        _holdExit($modal, () => $modal.modal('hide'));
    });

    document.addEventListener('click', function(e) {
        const exitElement = e.target.closest(GUARD_INTERNAL.ASYNC_EXIT_SELECTOR);
        if (!exitElement || exitElement.hasAttribute(GUARD_INTERNAL.STAY_IN_MODAL_ATTR)) return;

        const $modal = $(exitElement).closest(GUARD_INTERNAL.MODAL_SELECTOR);
        if ($modal.length === 0 || !_hasUnsavedChanges($modal)) return;

        e.preventDefault();
        e.stopPropagation();
        _holdExit($modal, () => exitElement.click());
    }, true);

    $(document).on('click', Hi.ATTR_V2_DISCARD_CHANGES_BTN_SELECTOR, function() {
        _discardChanges($(this).closest(Hi.ATTR_V2_UNSAVED_BANNER_SELECTOR));
    });

    $(document).on('click', Hi.ATTR_V2_KEEP_EDITING_BTN_SELECTOR, function() {
        _keepEditing($(this).closest(Hi.ATTR_V2_UNSAVED_BANNER_SELECTOR));
    });

})();
