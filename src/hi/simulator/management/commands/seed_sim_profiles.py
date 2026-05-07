"""
Seed the simulator with a curated suite of SimProfiles for manual
testing of the integration sync flows.

Five profiles, each designed to exercise a specific scenario:

  * empty            — zero items in every integration. Tests the
                       initial-import-with-nothing path and the
                       refresh-against-emptied-upstream path.
  * baseline         — the realistic small-install set. Mixed HASS
                       device types, a handful of HomeBox items, a
                       few ZM monitors. Used as the *before* state
                       for delta tests.
  * baseline-changed — same shape as baseline, with deltas in every
                       integration. The pair (baseline ↔
                       baseline-changed) is designed to exercise all
                       five sync-result categories — created,
                       updated, reconnected, detached, removed — in
                       a single flip back-and-forth. See "Operator
                       workflow for full-category coverage" below.
  * hass-zoo         — one HASS entity of every supported type.
                       Visual / grouping coverage for the HASS
                       converter; HomeBox/ZM stay empty.
  * volume           — large counts (30 HASS, 25 HomeBox, 10 ZM
                       monitors). Stresses modal list overflow
                       scrolling and dispatcher group sizing.

Re-running the command is a no-op when the named profile exists.
Pass ``--reset`` to delete the matching profile (and its entities)
before recreating.

Operator workflow for full-category coverage (sync result modal
manual validation):

  1. Switch simulator to ``baseline``. Sync HI. Two entities
     whose names start with ``★ Custom Attr Needed ★`` will be
     imported (HASS and ZM only — HomeBox sets
     ``can_add_custom_attributes = False`` by design, so HB
     entities cannot participate in the detach/reconnect cycle
     and have no anchor item). Open each in entity-edit and add
     ANY custom attribute (e.g., a "Note" attribute with any
     value). The custom attribute is what flips them onto the
     preserve-with-user-data path when they later disappear
     upstream.
  2. Switch simulator to ``baseline-changed``. Refresh sync.
     The result modal shows:
       - Created: three new items present only in baseline-changed
       - Updated: three items renamed / metadata-changed
       - Removed: three items absent here, no user attribute
       - Detached: two ★-prefixed items (HASS, ZM) absent here,
         with the user attribute the operator added in step 1
         retained
       - (Reconnected is empty on this direction)
  3. Switch simulator back to ``baseline``. Refresh sync.
     The result modal shows:
       - Reconnected: the two ★-prefixed items (HASS, ZM) rejoin
         via the secondary-match path; their custom attributes
         are intact
       - Created: the three previously-Removed items return as
         fresh entities (no previous_integration_id, so no
         reconnect — they come back as duplicates would, but
         since the originals were hard-deleted there's no
         duplication, just re-creation)
       - Updated: the renames / changes swap back
       - Removed: the three baseline-changed-only items are
         dropped (no user attributes anchored, so hard-deleted)
       - (Detached is empty on this direction unless extra
         attributes were anchored on items unique to
         baseline-changed)
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from hi.simulator.enums import SimEntityType
from hi.simulator.models import DbSimEntity, SimProfile
from hi.simulator.services.hass.sim_models import (
    HassInsteonDimmerLightSwitchFields,
    HassInsteonDualBandLightSwitchFields,
    HassInsteonLightSwitchFields,
    HassInsteonMotionDetectorFields,
    HassInsteonOpenCloseSensorFields,
    HassInsteonOutletFields,
)
from hi.simulator.services.homebox.sim_models import (
    HomeBoxInventoryItemFields,
)
from hi.simulator.services.zoneminder.sim_models import (
    ZmMonitorSimEntityFields,
    ZmServerSimEntityFields,
)


PROFILE_NAMES = [
    'empty',
    'baseline',
    'baseline-changed',
    'hass-zoo',
    'volume',
]


class Command(BaseCommand):
    help = (
        'Seed the simulator with a curated set of SimProfiles for '
        'integration sync testing (empty, baseline, baseline-changed, '
        'hass-zoo, volume).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action = 'store_true',
            help = (
                'Delete and recreate any of the seeded profiles that '
                'already exist. Default behavior is to leave existing '
                'profiles untouched.'
            ),
        )
        parser.add_argument(
            '--only',
            nargs = '+',
            choices = PROFILE_NAMES,
            help = 'Restrict seeding to the named profile(s).',
        )

    def handle(self, *args, **options):
        targets = options.get('only') or PROFILE_NAMES
        reset = options.get('reset', False)

        builders = {
            'empty': self._build_empty,
            'baseline': self._build_baseline,
            'baseline-changed': self._build_baseline_changed,
            'hass-zoo': self._build_hass_zoo,
            'volume': self._build_volume,
        }

        for name in targets:
            self._seed_profile(
                name = name,
                builder = builders[name],
                reset = reset,
            )

    # ----- profile orchestration -----

    def _seed_profile(self, name, builder, reset):
        existing = SimProfile.objects.filter(name = name).first()
        if existing:
            if not reset:
                self.stdout.write(
                    f'  skip  {name}: already exists '
                    '(pass --reset to recreate)'
                )
                return
            self.stdout.write(f'  reset  {name}: deleting existing profile')
            existing.delete()  # cascades to db_sim_entities

        with transaction.atomic():
            profile = SimProfile.objects.create(name = name)
            count = builder(profile)
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ok    {name}: created with {count} entit'
                    f'{"y" if count == 1 else "ies"}'
                )
            )

    # ----- builders -----

    def _build_empty(self, profile: SimProfile) -> int:
        return 0

    def _build_baseline(self, profile: SimProfile) -> int:
        # HASS: one of each common device kind, plus a ★-prefixed
        # item that the operator anchors with a custom attribute
        # before flipping to baseline-changed (drives the
        # detach/reconnect cycle on the HASS side).
        self._add_hass_light_switch( profile, 'Garage Light'   , '01.AA.01' )
        self._add_hass_dimmer(       profile, 'Den Lamp'       , '01.AA.02' )
        self._add_hass_motion(       profile, 'Hallway Motion' , '01.AA.03' )
        self._add_hass_open_close(   profile, 'Front Door'     , '01.AA.04' )
        self._add_hass_outlet(       profile, 'Kitchen Outlet' , '01.AA.05' )
        self._add_hass_light_switch(
            profile, '★ Custom Attr Needed ★ Office Light', '01.AA.10',
        )

        # HomeBox: 4 items with mixed metadata richness. No
        # ★-prefixed anchor here: HomeBox sets
        # ``can_add_custom_attributes = False`` (the converter is
        # the source of truth for HB item attributes), so the
        # operator cannot add a custom attribute on the HI side and
        # the detach/reconnect cycle does not apply to HB. ``item_id``
        # is the per-item stable id used by the integration's
        # change-detection — kept identical across baseline /
        # baseline-changed for items that should be 'the same item'.
        self._add_homebox_item(
            profile, 'Cordless Drill',
            item_id = 'cordless-drill',
            description = 'DeWalt 20V 1/2-inch drill driver',
            manufacturer = 'DeWalt',
            model_number = 'DCD777',
            serial_number = 'DW-100231',
            quantity = 1,
        )
        self._add_homebox_item(
            profile, 'Stud Finder',
            item_id = 'stud-finder',
            manufacturer = 'Franklin Sensors',
            quantity = 1,
        )
        self._add_homebox_item(
            profile, 'Soldering Iron Kit',
            item_id = 'soldering-iron-kit',
            description = 'Adjustable temp 60W with tips',
            quantity = 2,
        )
        self._add_homebox_item(
            profile, 'Spare Light Bulbs',
            item_id = 'spare-light-bulbs',
            quantity = 12,
        )

        # ZoneMinder: 1 server (singleton) + 2 monitors + a
        # ★-prefixed monitor anchor for the ZM detach/reconnect
        # cycle.
        self._add_zm_server( profile )
        self._add_zm_monitor( profile, 'Front Door Camera' , monitor_id = 1 )
        self._add_zm_monitor( profile, 'Driveway Camera'   , monitor_id = 2 )
        self._add_zm_monitor(
            profile, '★ Custom Attr Needed ★ Backyard Camera',
            monitor_id = 5,
        )

        return profile.db_sim_entities.count()

    def _build_baseline_changed(self, profile: SimProfile) -> int:
        # Designed as the partner of baseline so that flipping the
        # simulator between the two profiles and Refreshing
        # exercises every one of the five sync-result categories
        # (created / updated / reconnected / detached / removed)
        # in a single click. See the module docstring for the
        # operator workflow that drives the detach/reconnect path
        # via user-attribute anchoring.

        # HASS deltas vs baseline:
        #   Garage Light       — kept (no change)
        #   Den Lamp           — RENAMED to "Den Reading Lamp" (update)
        #   Hallway Motion     — kept
        #   Front Door         — REMOVED (no user attribute → hard delete)
        #   Kitchen Outlet     — kept
        #   ★ Office Light     — ABSENT here; with a user attribute
        #                        anchored on the HI side it takes
        #                        the preserve path → Detached
        #   <new> Patio Switch — ADDED (create)
        self._add_hass_light_switch( profile, 'Garage Light'     , '01.AA.01' )
        self._add_hass_dimmer(       profile, 'Den Reading Lamp' , '01.AA.02' )
        self._add_hass_motion(       profile, 'Hallway Motion'   , '01.AA.03' )
        # Front Door (01.AA.04) intentionally absent.
        self._add_hass_outlet(       profile, 'Kitchen Outlet'   , '01.AA.05' )
        self._add_hass_light_switch( profile, 'Patio Switch'     , '01.AA.06' )
        # Office Light (01.AA.10) intentionally absent — its HI-side
        # entity has the user-anchored custom attribute and takes
        # the detach path on the first sync after switching here.

        # HomeBox deltas:
        #   Cordless Drill   — kept (same item_id, same content)
        #   Stud Finder      — same item_id, manufacturer changed
        #                      (attribute update path)
        #   Soldering Iron   — REMOVED (item_id absent, no user attr)
        #   Spare Bulbs      — kept (same item_id, same content)
        #   <new> Caulk Gun  — ADDED (new item_id)
        # No HB detach/reconnect anchor — see baseline's HB section.
        # Identity carries via ``item_id`` (the simulator's stable
        # API id), not row order — so the order here doesn't matter
        # for change-detection.
        self._add_homebox_item(
            profile, 'Cordless Drill',
            item_id = 'cordless-drill',
            description = 'DeWalt 20V 1/2-inch drill driver',
            manufacturer = 'DeWalt',
            model_number = 'DCD777',
            serial_number = 'DW-100231',
            quantity = 1,
        )
        self._add_homebox_item(
            profile, 'Stud Finder',
            item_id = 'stud-finder',
            manufacturer = 'Bosch',  # changed from 'Franklin Sensors'
            quantity = 1,
        )
        self._add_homebox_item(
            profile, 'Spare Light Bulbs',
            item_id = 'spare-light-bulbs',
            quantity = 12,
        )
        self._add_homebox_item(
            profile, 'Caulk Gun',
            item_id = 'caulk-gun',
            description = '10-oz cartridge gun, dripless',
            quantity = 1,
        )

        # ZoneMinder deltas:
        #   ZM Server           — kept
        #   Front Door Camera   — RENAMED to "Front Porch Camera"
        #   Driveway Camera     — REMOVED
        #   ★ Backyard Camera   — ABSENT (monitor_id 5 absent) →
        #                         Detached via user-attribute anchor
        #   <new> Garage Camera — ADDED (monitor_id 3); deliberately
        #                         not named "Backyard Camera" to
        #                         avoid colliding with the
        #                         ★-prefixed Detached anchor when
        #                         flipping back.
        self._add_zm_server( profile )
        self._add_zm_monitor( profile, 'Front Porch Camera' , monitor_id = 1 )
        self._add_zm_monitor( profile, 'Garage Camera'      , monitor_id = 3 )
        # monitor_id 5 (Backyard Camera) intentionally absent.

        return profile.db_sim_entities.count()

    def _build_hass_zoo(self, profile: SimProfile) -> int:
        # One of every HASS sim entity definition type.
        self._add_hass_light_switch( profile, 'Zoo Light Switch'     , '01.BB.01' )
        self._add_hass_dimmer(       profile, 'Zoo Dimmer'           , '01.BB.02' )
        self._add_hass_dual_band(    profile, 'Zoo Dual Band Switch' , '01.BB.03' )
        self._add_hass_motion(       profile, 'Zoo Motion'           , '01.BB.04' )
        self._add_hass_open_close(   profile, 'Zoo Open/Close'       , '01.BB.05' )
        self._add_hass_outlet(       profile, 'Zoo Outlet'           , '01.BB.06' )
        return profile.db_sim_entities.count()

    def _build_volume(self, profile: SimProfile) -> int:
        # 30 HASS items spread across types with a heavy bias toward
        # the most common (lights). Insteon addresses are sequential
        # under the 01.CC.* prefix to avoid colliding with other
        # profiles if they happen to share a database load.
        light_types = [
            self._add_hass_light_switch,
            self._add_hass_dimmer,
            self._add_hass_dual_band,
        ]
        for index in range(20):
            adder = light_types[index % len(light_types)]
            adder(profile, f'Volume Light {index + 1:02}',
                  f'01.CC.{index + 1:02X}')
        for index in range(5):
            self._add_hass_motion(
                profile, f'Volume Motion {index + 1:02}',
                f'01.CD.{index + 1:02X}',
            )
        for index in range(3):
            self._add_hass_open_close(
                profile, f'Volume Door {index + 1:02}',
                f'01.CE.{index + 1:02X}',
            )
        for index in range(2):
            self._add_hass_outlet(
                profile, f'Volume Outlet {index + 1:02}',
                f'01.CF.{index + 1:02X}',
            )

        # 25 HomeBox items, varied metadata.
        for index in range(25):
            self._add_homebox_item(
                profile,
                f'Volume Item {index + 1:03}',
                item_id = f'volume-item-{index + 1:03}',
                description = (
                    f'Stress-test inventory item #{index + 1}'
                    if index % 3 == 0 else ''
                ),
                manufacturer = 'Acme' if index % 5 == 0 else '',
                quantity = (index % 4) + 1,
            )

        # ZM: 1 server + 10 monitors.
        self._add_zm_server(profile)
        for index in range(10):
            self._add_zm_monitor(
                profile,
                f'Volume Camera {index + 1:02}',
                monitor_id = 100 + index,
            )

        return profile.db_sim_entities.count()

    # ----- per-integration row builders -----

    def _add_hass_light_switch(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            simulator_id = 'hass',
            fields_class = HassInsteonLightSwitchFields,
            sim_entity_type = SimEntityType.LIGHT,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_dimmer(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            simulator_id = 'hass',
            fields_class = HassInsteonDimmerLightSwitchFields,
            sim_entity_type = SimEntityType.LIGHT,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_dual_band(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            simulator_id = 'hass',
            fields_class = HassInsteonDualBandLightSwitchFields,
            sim_entity_type = SimEntityType.LIGHT,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_motion(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            simulator_id = 'hass',
            fields_class = HassInsteonMotionDetectorFields,
            sim_entity_type = SimEntityType.MOTION_SENSOR,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_open_close(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            simulator_id = 'hass',
            fields_class = HassInsteonOpenCloseSensorFields,
            sim_entity_type = SimEntityType.OPEN_CLOSE_SENSOR,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_outlet(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            simulator_id = 'hass',
            fields_class = HassInsteonOutletFields,
            sim_entity_type = SimEntityType.ELECTRICAL_OUTLET,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_homebox_item(self, profile, name, **fields_kwargs):
        kwargs = {'name': name}
        kwargs.update(fields_kwargs)
        self._create_db_entity(
            profile = profile,
            simulator_id = 'hb',
            fields_class = HomeBoxInventoryItemFields,
            sim_entity_type = SimEntityType.OTHER,
            fields_kwargs = kwargs,
        )

    def _add_zm_server(self, profile):
        self._create_db_entity(
            profile = profile,
            simulator_id = 'zm',
            fields_class = ZmServerSimEntityFields,
            sim_entity_type = SimEntityType.SERVICE,
            fields_kwargs = {'name': 'ZM Server'},
        )

    def _add_zm_monitor(self, profile, name, monitor_id):
        self._create_db_entity(
            profile = profile,
            simulator_id = 'zm',
            fields_class = ZmMonitorSimEntityFields,
            sim_entity_type = SimEntityType.MOTION_SENSOR,
            fields_kwargs = {'name': name, 'monitor_id': monitor_id},
        )

    # ----- low-level row creator -----

    def _create_db_entity(self,
                          profile: SimProfile,
                          simulator_id: str,
                          fields_class,
                          sim_entity_type: SimEntityType,
                          fields_kwargs: dict):
        # Instantiate the dataclass to get a validated, defaults-filled
        # instance, then serialize via the same to_json_dict() the
        # simulator uses at runtime — keeps the persisted shape in
        # lock-step with how the simulator reads it back.
        fields_instance = fields_class(**fields_kwargs)
        DbSimEntity.objects.create(
            sim_profile = profile,
            simulator_id = simulator_id,
            entity_fields_class_id = fields_class.class_id(),
            sim_entity_type_str = str(sim_entity_type),
            sim_entity_fields_json = fields_instance.to_json_dict(),
        )
