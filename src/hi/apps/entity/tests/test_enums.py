import logging

from hi.apps.entity.enums import (
    EntityType,
    EntityStateType,
    EntityGroupType,
)
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityStateTypeDefaultRole(BaseTestCase):

    def test_every_entity_state_type_resolves_to_a_role(self):
        # Locks in the type-default coverage convention: every
        # EntityStateType has a same-named EntityStateRole member.
        # Adding an EntityStateType without the matching role would
        # KeyError at runtime; this test surfaces that at test time.
        for entity_state_type in EntityStateType:
            role = entity_state_type.default_role()
            self.assertEqual(role.name, entity_state_type.name)
        return


class TestEntityGroupTypeAssignments(BaseTestCase):
    """Pin a sample of EntityType → EntityGroupType assignments that
    the rebalance settled on. These are the load-bearing cases —
    things a user would obviously expect to find in a given bucket.
    The full assignment table lives in the enum itself; the
    coverage test below ensures no leaf type slips through."""

    def test_automation_subsumes_lights_outlets_switches_and_actuators(self):
        for et in (
                EntityType.LIGHT,
                EntityType.ELECTRICAL_OUTLET,
                EntityType.ON_OFF_SWITCH,
                EntityType.WALL_SWITCH,
                EntityType.OPEN_CLOSE_ACTUATOR,
                EntityType.GARAGE_DOOR_OPENER,
                EntityType.DOOR_LOCK,
                EntityType.CONTROLLER,
                EntityType.IRRIGATION_CONTROLLER):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.AUTOMATION,
                msg=f'{et.name} expected in AUTOMATION',
            )

    def test_security_carries_alarm_sensors(self):
        for et in (
                EntityType.CAMERA,
                EntityType.MOTION_SENSOR,
                EntityType.OPEN_CLOSE_SENSOR,
                EntityType.SMOKE_DETECTOR,
                EntityType.CARBON_MONOXIDE_DETECTOR,
                EntityType.GAS_DETECTOR,
                EntityType.LEAK_SENSOR,
                EntityType.RADON_DETECTOR):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.SECURITY,
                msg=f'{et.name} expected in SECURITY',
            )

    def test_sensors_carries_measurement_devices(self):
        # SENSORS is the new home for pure-measurement devices,
        # distinct from SECURITY's "is something wrong?" sensors.
        for et in (
                EntityType.BAROMETER,
                EntityType.THERMOMETER,
                EntityType.HYGROMETER,
                EntityType.LIGHT_SENSOR,
                EntityType.TIME_SOURCE,
                EntityType.WEATHER_STATION):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.SENSORS,
                msg=f'{et.name} expected in SENSORS',
            )

    def test_appliances_absorbs_hvac_and_water_treatment(self):
        # HVAC and water-treatment appliances landed in APPLIANCES
        # in the rebalance — the old CLIMATE bucket is gone.
        for et in (
                EntityType.REFRIGERATOR,
                EntityType.FREEZER,
                EntityType.DISHWASHER,
                EntityType.WATER_HEATER,
                EntityType.HVAC_FURNACE,
                EntityType.HVAC_AIR_HANDLER,
                EntityType.HVAC_CONDENSER,
                EntityType.HVAC_MINI_SPLIT,
                EntityType.THERMOSTAT,
                EntityType.HUMIDIFIER,
                EntityType.EXHAUST_FAN,
                EntityType.WATER_FILTER,
                EntityType.WATER_SOFTENER):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.APPLIANCES,
                msg=f'{et.name} expected in APPLIANCES',
            )

    def test_pool_is_dedicated_bucket(self):
        for et in (
                EntityType.POOL_FILTER,
                EntityType.POOL_HEATER,
                EntityType.POOL_PUMP,
                EntityType.POOL_SWG):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.POOL,
                msg=f'{et.name} expected in POOL',
            )

    def test_electrical_carries_in_home_distribution_and_motors(self):
        # ELECTRICAL is the in-home electrical infrastructure;
        # incoming-service meters live in UTILITIES. Pumps and
        # motors live here because they're driven electrically and
        # don't fit a domain-specific bucket like POOL.
        for et in (
                EntityType.ELECTRIC_PANEL,
                EntityType.ELECTRIC_WIRE,
                EntityType.CONTROL_WIRE,
                EntityType.GENERATOR,
                EntityType.UPS,
                EntityType.INVERTER,
                EntityType.BATTERY_STORAGE,
                EntityType.SOLAR_PANEL,
                EntityType.EV_CHARGER,
                EntityType.MOTOR,
                EntityType.PUMP,
                EntityType.SUMP_PUMP):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.ELECTRICAL,
                msg=f'{et.name} expected in ELECTRICAL',
            )

    def test_utilities_carries_incoming_services(self):
        # UTILITIES is the incoming-service side: meters, supply
        # lines, telecom inflow. In-home electrical distribution
        # lives in ELECTRICAL.
        for et in (
                EntityType.ELECTRICITY_METER,
                EntityType.GAS_METER,
                EntityType.WATER_METER,
                EntityType.GAS_LINE,
                EntityType.WATER_LINE,
                EntityType.SEWER_LINE,
                EntityType.WATER_SHUTOFF_VALVE,
                EntityType.ANTENNA,
                EntityType.SATELLITE_DISH):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.UTILITIES,
                msg=f'{et.name} expected in UTILITIES',
            )

    def test_tools_carries_yard_and_hand_tools(self):
        for et in (
                EntityType.TOOL,
                EntityType.HEDGE_TRIMMER,
                EntityType.LAWN_MOWER,
                EntityType.LEAF_BLOWER,
                EntityType.POWER_WASHER,
                EntityType.TRIMMER):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.TOOLS,
                msg=f'{et.name} expected in TOOLS',
            )

    def test_outdoors_carries_vegetation_fencing_and_irrigation(self):
        # OUTDOORS no longer holds outdoor power tools (they
        # moved to TOOLS) or pool equipment (POOL). Vegetation +
        # fencing + irrigation hardware remain.
        for et in (
                EntityType.PLANT,
                EntityType.TREE,
                EntityType.FENCE,
                EntityType.GREENHOUSE,
                EntityType.SPRINKLER_HEAD,
                EntityType.SPRINKLER_VALVE,
                EntityType.SPRINKLER_WIRE):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.OUTDOORS,
                msg=f'{et.name} expected in OUTDOORS',
            )

    def test_structural_carries_built_in_structure(self):
        # The garage split: GARAGE_DOOR is structural; the opener
        # is in AUTOMATION. AREA lives here because an "area" in
        # HI is a spatial region of the home — structural by nature.
        for et in (
                EntityType.AREA,
                EntityType.DOOR,
                EntityType.GARAGE_DOOR,
                EntityType.WINDOW,
                EntityType.SKYLIGHT,
                EntityType.ATTIC_STAIRS,
                EntityType.WALL,
                EntityType.FIREPLACE):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.STRUCTURAL,
                msg=f'{et.name} expected in STRUCTURAL',
            )

    def test_general_is_the_named_catchall(self):
        # GENERAL is the named catchall — every EntityType is
        # explicitly assigned, so there's no silent fallback
        # bucket. EntityType.OTHER lives here too.
        for et in (
                EntityType.AUTOMOBILE,
                EntityType.CONSUMABLE,
                EntityType.OTHER):
            self.assertEqual(
                EntityGroupType.from_entity_type(et),
                EntityGroupType.GENERAL,
                msg=f'{et.name} expected in GENERAL',
            )


class TestEntityGroupTypeInvariants(BaseTestCase):
    """Structural invariants that must hold across any future
    bucket rebalance."""

    def test_every_entity_type_is_assigned_to_exactly_one_bucket(self):
        """Full-coverage contract: every ``EntityType`` is assigned
        to exactly one ``EntityGroupType`` bucket.

        Pins the no-silent-fallback contract. Adding a new
        EntityType without assigning it to a bucket would silently
        route it to ``GENERAL`` via ``cls.default()``; this test
        forces the author to make an explicit assignment."""
        mapped: dict = {}
        for group in EntityGroupType:
            for entity_type in group.entity_type_set:
                self.assertNotIn(
                    entity_type, mapped,
                    msg=(
                        f'{entity_type.name} is in both '
                        f'{mapped.get(entity_type)} and {group.name} '
                        f'— buckets must be mutually exclusive'
                    ),
                )
                mapped[entity_type] = group.name

        for entity_type in EntityType:
            self.assertIn(
                entity_type, mapped,
                msg=(
                    f'{entity_type.name} is not assigned to any '
                    f'EntityGroupType — every leaf type must have '
                    f'an explicit bucket (no silent GENERAL fallback)'
                ),
            )

    def test_from_entity_type_resolves_consistently_with_membership(self):
        # The lookup function must agree with the entity_type_set
        # data — they're two views of the same fact.
        for group in EntityGroupType:
            for entity_type in group.entity_type_set:
                self.assertEqual(
                    EntityGroupType.from_entity_type(entity_type),
                    group,
                )

    def test_default_returns_general(self):
        self.assertEqual(EntityGroupType.default(), EntityGroupType.GENERAL)


class TestEntityGroupTypeLabels(BaseTestCase):
    """Pin the user-facing label contract."""

    def test_all_labels_are_non_empty_strings(self):
        for group in EntityGroupType:
            self.assertIsInstance(group.label, str)
            self.assertGreater(len(group.label), 0)

    def test_all_labels_are_unique(self):
        labels = [group.label for group in EntityGroupType]
        self.assertEqual(
            len(labels), len(set(labels)),
            msg='EntityGroupType labels must be unique for stable UI sort',
        )

    def test_specific_labels(self):
        # Pin the new bucket names so a rename surfaces here
        # rather than silently in the UI.
        expected = {
            EntityGroupType.APPLIANCES: 'Appliances',
            EntityGroupType.AUDIO_VISUAL: 'Audio/Visual',
            EntityGroupType.AUTOMATION: 'Automation',
            EntityGroupType.COMPUTERS: 'Computers',
            EntityGroupType.ELECTRICAL: 'Electrical',
            EntityGroupType.FIXTURES: 'Fixtures',
            EntityGroupType.GENERAL: 'General',
            EntityGroupType.OUTDOORS: 'Outdoors',
            EntityGroupType.POOL: 'Pool',
            EntityGroupType.SECURITY: 'Security',
            EntityGroupType.SENSORS: 'Sensors',
            EntityGroupType.STRUCTURAL: 'Structural',
            EntityGroupType.TOOLS: 'Tools',
            EntityGroupType.UTILITIES: 'Utilities',
        }
        for group, label in expected.items():
            self.assertEqual(group.label, label)
