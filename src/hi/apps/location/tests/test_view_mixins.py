"""Tests for ``LocationViewMixin.get_entity_svg_update_response``.

Pins the icon-vs-path selector-split contract documented in
``view_mixins.py`` and mirrored in ``entity_state_status.js``.
A regression here would silently re-introduce the parent-<g>-fill
cascade bug that obliterated the light bulb's outline on click-toggle.
"""

import json
from unittest.mock import MagicMock, patch

from hi.apps.location.view_mixins import LocationViewMixin
from hi.testing.base_test_case import BaseTestCase


class _MixinHost( LocationViewMixin ):
    """Concrete host for the mixin so tests can instantiate it."""
    pass


class TestGetEntitySvgUpdateResponse( BaseTestCase ):

    def _make_status_display_data( self, state_id: int, attribute_dict: dict ):
        """A minimal stand-in for ``EntityStateDisplayData``: needs only
        ``.entity_state.id`` and ``.attribute_dict`` for the method
        under test."""
        display_data = MagicMock()
        display_data.entity_state.id = state_id
        display_data.attribute_dict = attribute_dict
        return display_data

    def _invoke_and_parse(self, status_display_data_list):
        """Run the mixin method with a patched StatusDisplayManager and
        a patched ``EntityStateDisplayData`` (returns the prepared
        stand-ins). Returns the parsed JSON of the antinode response's
        ``setAttributes`` field."""
        host = _MixinHost()

        # The mixin walks ``entity_status_data.entity_state_status_data_list``
        # and wraps each entry in ``EntityStateDisplayData``. Patch
        # both surfaces: the manager call returns a synthetic
        # container, and ``EntityStateDisplayData(...)`` returns the
        # prepared stand-ins in order.
        container = MagicMock()
        container.entity_state_status_data_list = [
            MagicMock() for _ in status_display_data_list
        ]

        with patch(
                'hi.apps.location.view_mixins.StatusDisplayManager'
        ) as mock_manager_cls, patch(
                'hi.apps.location.view_mixins.EntityStateDisplayData',
                side_effect=status_display_data_list,
        ):
            mock_manager_cls.return_value.get_entity_status_data.return_value = container
            response = host.get_entity_svg_update_response(entity=MagicMock())

        payload = json.loads(response.content)
        return payload.get('setAttributes', {})

    def test_emits_both_selectors_with_correct_carve_out(self):
        """For a state whose ``attribute_dict`` carries the full
        SvgStatusStyle payload, the response must contain TWO
        selectors per state-id: the ``[data-status]`` selector with
        ONLY ``status``, and the ``[data-svg-style]`` selector with
        the full dict."""
        full = {
            'status': 'on',
            'stroke': 'yellow',
            'stroke-width': 2.0,
            'fill': 'yellow',
            'fill-opacity': 0.5,
        }
        set_attrs = self._invoke_and_parse([
            self._make_status_display_data(state_id=42, attribute_dict=full),
        ])

        icon_selector = '[data-state-id="42"][data-status]'
        path_selector = '[data-state-id="42"][data-svg-style]'

        self.assertIn(icon_selector, set_attrs)
        self.assertIn(path_selector, set_attrs)
        # Icon gets ``status`` ONLY: nothing else may cascade into
        # children of the <g> wrapper.
        self.assertEqual(set_attrs[icon_selector], {'status': 'on'})
        # Path gets the full presentation attribute set.
        self.assertEqual(set_attrs[path_selector], full)

    def test_empty_attribute_dict_emits_no_entry(self):
        """A state with an empty ``attribute_dict`` (e.g., the
        ``svg_status_style`` was None / unrecognized) must not
        contribute either selector to the response."""
        set_attrs = self._invoke_and_parse([
            self._make_status_display_data(state_id=99, attribute_dict={}),
        ])

        self.assertNotIn('[data-state-id="99"][data-status]', set_attrs)
        self.assertNotIn('[data-state-id="99"][data-svg-style]', set_attrs)

    def test_attribute_dict_without_status_still_emits_path_selector(self):
        """An attribute dict that has style attrs but no ``status``
        key must still produce the ``[data-svg-style]`` selector for
        path elements while skipping the ``[data-status]`` one."""
        style_only = { 'stroke': 'red', 'stroke-width': 3.0 }
        set_attrs = self._invoke_and_parse([
            self._make_status_display_data(state_id=7, attribute_dict=style_only),
        ])

        self.assertNotIn('[data-state-id="7"][data-status]', set_attrs)
        self.assertIn('[data-state-id="7"][data-svg-style]', set_attrs)
        self.assertEqual(set_attrs['[data-state-id="7"][data-svg-style]'], style_only)

    def test_multiple_states_each_produce_their_own_selector_pair(self):
        """Multiple states on one entity each contribute an independent
        selector pair keyed by their respective state ids."""
        a = { 'status': 'on', 'fill': 'yellow' }
        b = { 'status': 'off', 'fill': 'grey' }
        set_attrs = self._invoke_and_parse([
            self._make_status_display_data(state_id=1, attribute_dict=a),
            self._make_status_display_data(state_id=2, attribute_dict=b),
        ])

        self.assertEqual(set_attrs['[data-state-id="1"][data-status]'], {'status': 'on'})
        self.assertEqual(set_attrs['[data-state-id="1"][data-svg-style]'], a)
        self.assertEqual(set_attrs['[data-state-id="2"][data-status]'], {'status': 'off'})
        self.assertEqual(set_attrs['[data-state-id="2"][data-svg-style]'], b)
