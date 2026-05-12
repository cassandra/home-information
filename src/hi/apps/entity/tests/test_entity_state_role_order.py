import logging

from hi.apps.entity.entity_state_role_order import (
    DEFAULT_ENTITY_STATE_ROLE_ORDER,
    ENTITY_STATUS_VIEW_ORDERING,
    EntityStateRoleOrdering,
)
from hi.apps.entity.enums import EntityStateRole, EntityType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityStateRoleOrdering(BaseTestCase):

    def test_unoverridden_entity_type_uses_default_order(self):
        # OTHER has no override; resolved order matches the default.
        self.assertEqual(
            ENTITY_STATUS_VIEW_ORDERING.order_for( EntityType.OTHER ),
            DEFAULT_ENTITY_STATE_ROLE_ORDER,
        )
        return

    def test_thermostat_override_prefixes_default_tail(self):
        # Override is the prefix; remaining default-order roles follow,
        # deduplicated against the override.
        order = ENTITY_STATUS_VIEW_ORDERING.order_for( EntityType.THERMOSTAT )
        self.assertEqual( order[0], EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE )
        self.assertEqual( order[1], EntityStateRole.HUMIDITY )
        self.assertEqual( order[2], EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_LOW )
        self.assertEqual( order[3], EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE )
        self.assertEqual( order[4], EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_HIGH )
        return

    def test_sort_key_drives_thermostat_listing_order(self):
        # End-to-end: feeding a shuffled list of roles through sort_key
        # produces THERMOSTAT_CURRENT_TEMPERATURE first for a thermostat,
        # with the three setpoints in low / single / high order.
        shuffled = [
            EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_HIGH,
            EntityStateRole.HUMIDITY,
            EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
            EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
            EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_LOW,
        ]
        ordered = sorted(
            shuffled,
            key = lambda r: ENTITY_STATUS_VIEW_ORDERING.sort_key( r, EntityType.THERMOSTAT ),
        )
        self.assertEqual( ordered, [
            EntityStateRole.THERMOSTAT_CURRENT_TEMPERATURE,
            EntityStateRole.HUMIDITY,
            EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_LOW,
            EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE,
            EntityStateRole.THERMOSTAT_TARGET_TEMPERATURE_HIGH,
        ])
        return

    def test_parameterizable_for_parallel_orderings(self):
        # A separate instance with its own override map produces a
        # different resolved order — locks in that the class is
        # parameterizable for future parallel use cases (icon-status
        # selection, one-click controller selection).
        alt = EntityStateRoleOrdering(
            default_order = DEFAULT_ENTITY_STATE_ROLE_ORDER,
            overrides = {
                EntityType.OTHER: [ EntityStateRole.BATTERY_LEVEL ],
            },
        )
        self.assertEqual(
            alt.order_for( EntityType.OTHER )[0],
            EntityStateRole.BATTERY_LEVEL,
        )
        # The display ordering's resolution for OTHER is unaffected.
        self.assertEqual(
            ENTITY_STATUS_VIEW_ORDERING.order_for( EntityType.OTHER )[0],
            DEFAULT_ENTITY_STATE_ROLE_ORDER[0],
        )
        return
