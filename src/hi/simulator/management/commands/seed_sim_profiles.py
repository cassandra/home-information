"""
Seed the simulator with a curated suite of per-module SimProfiles for
manual testing of the integration sync flows.

Profiles are scoped to a single module (each service simulator owns its
own profile namespace), so the seed catalog is partitioned by module:

  HASS (hi.simulator.services.hass)
    * empty
    * baseline
    * baseline-changed
    * hass-zoo            — one HASS entity of every supported type

  HomeBox (hi.simulator.services.homebox)
    * empty
    * baseline
    * baseline-changed
    * volume              — 25 items, varied metadata

  ZoneMinder (hi.simulator.services.zoneminder)
    * empty
    * baseline
    * baseline-changed
    * volume              — 1 server + 10 monitors

  Frigate (hi.simulator.services.frigate)
    * empty
    * baseline
    * baseline-changed
    * volume              — 10 cameras

  NWS (hi.simulator.weather_sources.nws)
    * sample              — curated 8-alert catalog spanning event
                            types; every alert starts inactive so
                            the operator toggles individually to
                            exercise the active-alerts feed.

Re-running the command is a no-op for profiles that already exist.
Pass ``--reset`` to delete the matching profile (and its entities)
before recreating. Pass ``--module <short>`` (``hass``, ``homebox``,
``zoneminder``) to restrict seeding to one service's catalog.

Operator workflow for full-category coverage (sync result modal
manual validation): each module's ``baseline`` / ``baseline-changed``
pair is designed to exercise its own integration's sync results
independently. Switch the relevant module's profile selector between
the two and refresh sync to see created / updated / reconnected /
detached / removed transitions for that integration.

  1. Switch HASS to ``baseline``. Sync HI. An entity whose name
     starts with ``★ Custom Attr Needed ★`` will be imported.
     Open it in entity-edit and add ANY custom attribute (e.g., a
     ``Note`` attribute with any value). The custom attribute is
     what flips it onto the preserve-with-user-data path when it
     later disappears upstream.
  2. Repeat for ZM: switch ZoneMinder to ``baseline``, sync, add a
     custom attribute to its ★-prefixed monitor. (HomeBox sets
     ``can_add_custom_attributes = False`` by design, so HB
     entities cannot participate in the detach/reconnect cycle and
     have no anchor item.)
  3. Switch each module to its ``baseline-changed``. Refresh sync.
     The result modal shows per-module:
       - Created: new items present only in baseline-changed
       - Updated: items renamed / metadata-changed
       - Removed: items absent here, no user attribute
       - Detached: ★-prefixed items (HASS, ZM) absent here, with
         the user attribute the operator added retained
  4. Switch each module back to ``baseline``. Refresh sync.
     Reconnected: the ★-prefixed items rejoin via the
     secondary-match path; their custom attributes are intact.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from hi.simulator.profile.models import SimProfile
from hi.simulator.profile.profile_manager import ProfileManager
from hi.simulator.services.enums import SimEntityType
from hi.simulator.services.hass.apps import HassConfig
from hi.simulator.services.hass.sim_models import (
    HassCameraNoMotionSimEntityFields,
    HassCameraSimEntityFields,
    HassCarbonMonoxideDetectorFields,
    HassColorSmartBulbFields,
    HassFanFields,
    HassGarageCoverFields,
    HassGasDetectorFields,
    HassGenericCoverFields,
    HassInsteonDimmerLightSwitchFields,
    HassDoorContactSensorFields,
    HassInsteonDualBandLightSwitchFields,
    HassInsteonLightSwitchFields,
    HassInsteonMotionDetectorFields,
    HassInsteonOpenCloseSensorFields,
    HassInsteonOutletFields,
    HassComboMotionSensorFields,
    HassLockFields,
    HassMotionSensorFields,
    HassMultiFeatureFanFields,
    HassOccupancyLightSensorFields,
    HassOpeningSensorFields,
    HassOutletFields,
    HassPowerMeterFields,
    HassPresenceSensorFields,
    HassSmartBulbFields,
    HassSmokeDetectorFields,
    HassSmokeDetectorWithBatteryFields,
    HassSwitchFields,
    HassWaterLeakSensorFields,
    HassWeatherStationFields,
    HassTemperatureSensorFields,
    HassTempHumiditySensorFields,
    HassThermostatFields,
    HassHumiditySensorFields,
    HassWindowBlindCoverFields,
    HassWindowContactSensorFields,
)
from hi.simulator.services.frigate.apps import FrigateConfig
from hi.simulator.services.frigate.sim_models import (
    FrigateCameraSimEntityFields,
)
from hi.simulator.services.homebox.apps import HomeBoxConfig
from hi.simulator.services.homebox.attachment_catalog import AttachmentTemplate
from hi.simulator.services.homebox.sim_models import (
    HomeBoxInventoryItemFields,
)
from hi.simulator.services.models import DbSimEntity
from hi.simulator.services.zoneminder.apps import ZoneminderConfig
from hi.simulator.services.zoneminder.sim_models import (
    ZmMonitorSimEntityFields,
    ZmServerSimEntityFields,
)
from hi.simulator.weather_sources.nws.apps import NwsWeatherSimConfig
from hi.simulator.weather_sources.nws.models import NwsSimAlert


# Short module aliases for the --module CLI flag, mapped to the full
# AppConfig.name used as ``SimProfile.module_key``.
MODULE_SHORT_NAMES = {
    'hass': HassConfig.name,
    'homebox': HomeBoxConfig.name,
    'zoneminder': ZoneminderConfig.name,
    'frigate': FrigateConfig.name,
    'nws': NwsWeatherSimConfig.name,
}


class Command(BaseCommand):
    help = (
        'Seed the simulator with a curated set of per-module SimProfiles '
        'for integration sync testing. By default seeds all service '
        'modules (HASS, HomeBox, ZoneMinder); restrict with --module.'
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
            '--module',
            choices = sorted( MODULE_SHORT_NAMES.keys() ),
            help = (
                'Restrict seeding to a single service module. Default '
                'is to seed all service modules.'
            ),
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        module_filter = options.get('module')

        registry = self._build_registry()
        if module_filter:
            target_module_key = MODULE_SHORT_NAMES[ module_filter ]
            registry = [
                entry for entry in registry
                if entry[0] == target_module_key
            ]

        last_module_key = None
        for module_key, profile_name, builder in registry:
            if module_key != last_module_key:
                self.stdout.write( f'\n[{module_key}]' )
                last_module_key = module_key
            self._seed_profile(
                module_key = module_key,
                name = profile_name,
                builder = builder,
                reset = reset,
            )

    # ----- registry -----

    def _build_registry(self):
        """List of (module_key, profile_name, builder_callable).

        Order matters for output legibility — keep grouped by module.
        Each builder takes a freshly-created SimProfile and returns the
        count of DbSimEntity rows it created.
        """
        hass = HassConfig.name
        homebox = HomeBoxConfig.name
        zoneminder = ZoneminderConfig.name
        frigate = FrigateConfig.name
        nws = NwsWeatherSimConfig.name
        return [
            ( hass       , 'empty'            , self._build_empty ),
            ( hass       , 'baseline'         , self._build_hass_baseline ),
            ( hass       , 'baseline-changed' , self._build_hass_baseline_changed ),
            ( hass       , 'hass-zoo'         , self._build_hass_zoo ),

            ( homebox    , 'empty'            , self._build_empty ),
            ( homebox    , 'baseline'         , self._build_homebox_baseline ),
            ( homebox    , 'baseline-changed' , self._build_homebox_baseline_changed ),
            ( homebox    , 'volume'           , self._build_homebox_volume ),

            ( zoneminder , 'empty'            , self._build_empty ),
            ( zoneminder , 'baseline'         , self._build_zm_baseline ),
            ( zoneminder , 'baseline-changed' , self._build_zm_baseline_changed ),
            ( zoneminder , 'volume'           , self._build_zm_volume ),

            ( frigate    , 'empty'            , self._build_empty ),
            ( frigate    , 'baseline'         , self._build_frigate_baseline ),
            ( frigate    , 'baseline-changed' , self._build_frigate_baseline_changed ),
            ( frigate    , 'volume'           , self._build_frigate_volume ),

            ( nws        , 'sample'           , self._build_nws_sample ),
        ]

    # ----- profile orchestration -----

    def _seed_profile(self, module_key, name, builder, reset):
        existing = SimProfile.objects.filter(
            module_key = module_key, name = name,
        ).first()
        if existing:
            if not reset:
                self.stdout.write(
                    f'  skip   {name}: already exists '
                    '(pass --reset to recreate)'
                )
                return
            self.stdout.write( f'  reset  {name}: deleting existing profile' )
            existing.delete()  # cascades to db_sim_entities

        with transaction.atomic():
            profile = SimProfile.objects.create(
                module_key = module_key, name = name,
            )
            count = builder(profile)
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ok     {name}: created with {count} entit'
                    f'{"y" if count == 1 else "ies"}'
                )
            )

        # Notify the relevant module if the freshly-(re)created profile
        # is its currently-selected profile, so its in-memory caches
        # reload against the new entity set. Safe no-op when the
        # module hasn't registered a callback or the profile isn't
        # current.
        try:
            current = ProfileManager().get_current( module_key )
            if current.pk == profile.pk:
                ProfileManager().set_current( module_key, profile )
        except Exception:  # pragma: no cover - defensive on first-run
            pass

    # ----- module-agnostic builders -----

    def _build_empty(self, profile: SimProfile) -> int:
        return 0

    # ----- HASS builders -----

    def _build_hass_baseline(self, profile: SimProfile) -> int:
        # One of each common device kind, plus a ★-prefixed item that
        # the operator anchors with a custom attribute before flipping
        # to baseline-changed (drives the detach/reconnect cycle).
        self._add_hass_light_switch( profile, 'Garage Light'   , '01.AA.01' )
        self._add_hass_dimmer(       profile, 'Den Lamp'       , '01.AA.02' )
        self._add_hass_motion(       profile, 'Hallway Motion' , '01.AA.03' )
        self._add_hass_open_close(   profile, 'Front Door'     , '01.AA.04' )
        self._add_hass_outlet(       profile, 'Kitchen Outlet' , '01.AA.05' )
        self._add_hass_light_switch(
            profile, '★ Custom Attr Needed ★ Office Light', '01.AA.10',
        )
        return profile.db_sim_entities.count()

    def _build_hass_baseline_changed(self, profile: SimProfile) -> int:
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
        self._add_hass_outlet(       profile, 'Kitchen Outlet'   , '01.AA.05' )
        self._add_hass_light_switch( profile, 'Patio Switch'     , '01.AA.06' )
        return profile.db_sim_entities.count()

    def _build_hass_zoo(self, profile: SimProfile) -> int:
        # One of every HASS sim entity definition type. Subsumes the
        # historical cross-module "volume" stress case for HASS.
        self._add_hass_camera(           profile, 'Zoo Camera'          , 'zoo_camera' )
        self._add_hass_camera_no_motion( profile, 'Zoo Camera No Motion', 'zoo_camera_no_motion' )
        self._add_hass_light_switch(   profile, 'Zoo Insteon Light Switch'     , '01.BB.01' )
        self._add_hass_dimmer(         profile, 'Zoo Insteon Dimmer'           , '01.BB.02' )
        self._add_hass_dual_band(      profile, 'Zoo Insteon Dual Band Switch' , '01.BB.03' )
        self._add_hass_motion(         profile, 'Zoo Insteon Motion'           , '01.BB.04' )
        self._add_hass_open_close(     profile, 'Zoo Insteon Open/Close'       , '01.BB.05' )
        self._add_hass_outlet(         profile, 'Zoo Insteon Outlet'           , '01.BB.06' )
        self._add_hass_switch(         profile, 'Zoo Switch' )
        self._add_hass_motion_sensor(  profile, 'Zoo Motion' )
        self._add_hass_combo_motion_sensor( profile, 'Zoo Smart Motion' )
        self._add_hass_basic_outlet(   profile, 'Zoo Outlet' )
        self._add_hass_presence_sensor(  profile, 'Zoo Presence' )
        self._add_hass_opening_sensor(   profile, 'Zoo Opening' )
        self._add_hass_power_meter(      profile, 'Zoo Power Meter' )
        self._add_hass_weather_station(  profile, 'Zoo Weather Station' )
        self._add_hass_occupancy_light_sensor( profile, 'Zoo Room Sensor' )
        self._add_hass_water_leak_sensor( profile, 'Zoo Leak Sensor' )
        self._add_hass_smart_bulb(     profile, 'Zoo Smart Bulb' )
        self._add_hass_color_smart_bulb( profile, 'Zoo Color Bulb' )
        self._add_hass_door_contact(   profile, 'Zoo Door Contact' )
        self._add_hass_window_contact( profile, 'Zoo Window Contact' )
        self._add_hass_smoke_detector( profile, 'Zoo Smoke Detector' )
        self._add_hass_smoke_detector_with_battery( profile, 'Zoo Smoke Detector (Battery)' )
        self._add_hass_carbon_monoxide_detector( profile, 'Zoo CO Detector' )
        self._add_hass_gas_detector(   profile, 'Zoo Gas Detector' )
        self._add_hass_temperature_sensor( profile, 'Zoo Thermometer' )
        self._add_hass_temperature_sensor(
            profile, 'Zoo Thermometer Celsius', temperature_unit = '°C',
        )
        self._add_hass_humidity_sensor( profile, 'Zoo Hygrometer' )
        self._add_hass_temp_humidity_sensor( profile, 'Zoo Climate Sensor' )
        self._add_hass_lock(           profile, 'Zoo Lock' )
        self._add_hass_garage_cover(   profile, 'Zoo Garage' )
        self._add_hass_window_blind_cover( profile, 'Zoo Blind' )
        self._add_hass_generic_cover(  profile, 'Zoo Cover' )
        self._add_hass_ceiling_fan(    profile, 'Zoo Fan' )
        self._add_hass_multi_feature_fan( profile, 'Zoo Smart Fan' )
        self._add_hass_thermostat(     profile, 'Zoo Thermostat' )
        self._add_hass_thermostat(
            profile, 'Zoo Heater',
            hvac_modes = [ 'heat', 'off' ],
            fan_modes = [],
            temperature_unit = '°C',
        )
        return profile.db_sim_entities.count()

    # ----- HomeBox builders -----

    def _build_homebox_baseline(self, profile: SimProfile) -> int:
        # 4 items with mixed metadata richness. No ★-prefixed anchor
        # here: HomeBox sets ``can_add_custom_attributes = False`` (the
        # converter is the source of truth for HB item attributes), so
        # the operator cannot add a custom attribute on the HI side
        # and the detach/reconnect cycle does not apply to HB.
        # ``item_id`` is the per-item stable id used by the
        # integration's change-detection — kept identical across
        # baseline / baseline-changed for items that should be 'the
        # same item'.
        self._add_homebox_item(
            profile, 'Cordless Drill',
            item_id = 'cordless-drill',
            description = 'DeWalt 20V 1/2-inch drill driver',
            manufacturer = 'DeWalt',
            model_number = 'DCD777',
            serial_number = 'DW-100231',
            quantity = 1,
            attachment_keys = ','.join([
                AttachmentTemplate.MANUAL.key,
                AttachmentTemplate.RECEIPT.key,
            ]),
        )
        self._add_homebox_item(
            profile, 'Stud Finder',
            item_id = 'stud-finder',
            manufacturer = 'Franklin Sensors',
            quantity = 1,
            attachment_keys = AttachmentTemplate.PHOTO.key,
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
        return profile.db_sim_entities.count()

    def _build_homebox_baseline_changed(self, profile: SimProfile) -> int:
        # HomeBox deltas vs baseline:
        #   Cordless Drill   — kept (same item_id, attachment churn)
        #   Stud Finder      — same item_id, manufacturer changed
        #                      (attribute update path)
        #   Soldering Iron   — REMOVED (item_id absent, no user attr)
        #   Spare Bulbs      — kept (same item_id, same content)
        #   <new> Caulk Gun  — ADDED (new item_id)
        self._add_homebox_item(
            profile, 'Cordless Drill',
            item_id = 'cordless-drill',
            description = 'DeWalt 20V 1/2-inch drill driver',
            manufacturer = 'DeWalt',
            model_number = 'DCD777',
            serial_number = 'DW-100231',
            quantity = 1,
            # Attachment churn vs baseline: receipt removed, warranty
            # added; manual kept. Exercises attachment add+remove
            # paths in the refresh sync.
            attachment_keys = ','.join([
                AttachmentTemplate.MANUAL.key,
                AttachmentTemplate.WARRANTY.key,
            ]),
        )
        self._add_homebox_item(
            profile, 'Stud Finder',
            item_id = 'stud-finder',
            manufacturer = 'Bosch',  # changed from 'Franklin Sensors'
            quantity = 1,
            attachment_keys = AttachmentTemplate.PHOTO.key,
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
        return profile.db_sim_entities.count()

    def _build_homebox_volume(self, profile: SimProfile) -> int:
        # 25 items, varied metadata richness. Stresses HB list rendering
        # and the inventory pagination/scroll behavior.
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
        return profile.db_sim_entities.count()

    # ----- ZoneMinder builders -----

    def _build_zm_baseline(self, profile: SimProfile) -> int:
        # 1 server (singleton) + 2 monitors + a ★-prefixed monitor
        # anchor for the ZM detach/reconnect cycle.
        self._add_zm_server( profile )
        self._add_zm_monitor( profile, 'Front Door Camera' , monitor_id = 1 )
        self._add_zm_monitor( profile, 'Driveway Camera'   , monitor_id = 2 )
        self._add_zm_monitor(
            profile, '★ Custom Attr Needed ★ Backyard Camera',
            monitor_id = 5,
        )
        return profile.db_sim_entities.count()

    def _build_zm_baseline_changed(self, profile: SimProfile) -> int:
        # ZoneMinder deltas vs baseline:
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
        return profile.db_sim_entities.count()

    def _build_zm_volume(self, profile: SimProfile) -> int:
        # 1 server + 10 monitors. Stresses dispatcher group sizing.
        self._add_zm_server( profile )
        for index in range(10):
            self._add_zm_monitor(
                profile,
                f'Volume Camera {index + 1:02}',
                monitor_id = 100 + index,
            )
        return profile.db_sim_entities.count()

    # ----- Frigate builders -----

    def _build_frigate_baseline(self, profile: SimProfile) -> int:
        # 3 cameras + a ★-prefixed camera anchor for the detach/reconnect
        # cycle.
        self._add_frigate_camera( profile, 'Front Yard', camera_name = 'front_yard' )
        self._add_frigate_camera( profile, 'Driveway'  , camera_name = 'driveway' )
        self._add_frigate_camera( profile, 'Kitchen'   , camera_name = 'kitchen' )
        self._add_frigate_camera(
            profile, '★ Custom Attr Needed ★ Backyard Camera',
            camera_name = 'backyard',
        )
        return profile.db_sim_entities.count()

    def _build_frigate_baseline_changed(self, profile: SimProfile) -> int:
        # Frigate deltas vs baseline:
        #   Front Yard       — kept
        #   Driveway         — REMOVED (no user attr → hard delete)
        #   Kitchen          — kept
        #   ★ Backyard       — ABSENT (camera_name absent) → Detached
        #                       via user-attribute anchor
        #   <new> Patio      — ADDED (new camera_name)
        self._add_frigate_camera( profile, 'Front Yard', camera_name = 'front_yard' )
        self._add_frigate_camera( profile, 'Kitchen'   , camera_name = 'kitchen' )
        self._add_frigate_camera( profile, 'Patio'     , camera_name = 'patio' )
        return profile.db_sim_entities.count()

    def _build_frigate_volume(self, profile: SimProfile) -> int:
        # 10 cameras.
        for index in range(10):
            self._add_frigate_camera(
                profile,
                f'Volume Camera {index + 1:02}',
                camera_name = f'volume_camera_{index + 1:02}',
            )
        return profile.db_sim_entities.count()

    # ----- NWS builders -----

    def _build_nws_sample(self, profile: SimProfile) -> int:
        # 8-alert catalog spanning event types and severities. Every
        # alert is inactive by default so the operator toggles each on
        # individually to drive the active-alerts feed through one
        # event type at a time. Severity / certainty / urgency follow
        # the canonical CAP pairings the NWS issues for each product.
        area = 'Demo County, ZZ'
        self._add_nws_alert(
            profile,
            event_code = 'TOR',
            event_name = 'Tornado Warning',
            severity = 'Extreme', certainty = 'Observed', urgency = 'Immediate',
            category = 'met', area_desc = area,
            headline = 'Tornado Warning issued for Demo County',
            description = (
                'At 4:15 PM, a confirmed tornado was located near Demo '
                'Town, moving northeast at 35 mph. This is a particularly '
                'dangerous situation.'
            ),
            instruction = (
                'TAKE COVER NOW! Move to a basement or interior room on '
                'the lowest floor of a sturdy building. Avoid windows.'
            ),
        )
        self._add_nws_alert(
            profile,
            event_code = 'HUW',
            event_name = 'Hurricane Warning',
            severity = 'Extreme', certainty = 'Likely', urgency = 'Expected',
            category = 'met', area_desc = area,
            headline = 'Hurricane Warning in effect for Demo County',
            description = (
                'Hurricane conditions are expected somewhere within the '
                'warning area within 36 hours. Devastating wind damage '
                'and life-threatening storm surge are anticipated.'
            ),
            instruction = (
                'Complete preparations for hurricane-force winds and '
                'storm surge. Follow evacuation orders from local '
                'officials.'
            ),
        )
        self._add_nws_alert(
            profile,
            event_code = 'SVR',
            event_name = 'Severe Thunderstorm Warning',
            severity = 'Severe', certainty = 'Observed', urgency = 'Immediate',
            category = 'met', area_desc = area,
            headline = 'Severe Thunderstorm Warning for Demo County',
            description = (
                'At 3:50 PM, severe thunderstorms were located along a '
                'line moving east at 40 mph. Hazards include 60 mph wind '
                'gusts and quarter-size hail.'
            ),
            instruction = (
                'For your protection move to an interior room on the '
                'lowest floor of a building.'
            ),
        )
        self._add_nws_alert(
            profile,
            event_code = 'FFW',
            event_name = 'Flash Flood Warning',
            severity = 'Severe', certainty = 'Likely', urgency = 'Immediate',
            category = 'met', area_desc = area,
            headline = 'Flash Flood Warning for Demo County',
            description = (
                'Flash flooding is ongoing or expected to begin shortly. '
                'Between 1 and 3 inches of rain have fallen. Additional '
                'rainfall amounts of 1 to 2 inches are possible.'
            ),
            instruction = (
                'Turn around, don\'t drown when encountering flooded '
                'roads. Most flood deaths occur in vehicles.'
            ),
        )
        self._add_nws_alert(
            profile,
            event_code = 'WSW',
            event_name = 'Winter Storm Warning',
            severity = 'Moderate', certainty = 'Likely', urgency = 'Expected',
            category = 'met', area_desc = area,
            headline = 'Winter Storm Warning issued for Demo County',
            description = (
                'Heavy snow expected. Total snow accumulations of 8 to '
                '12 inches. Winds gusting as high as 35 mph.'
            ),
            instruction = (
                'Travel could be very difficult to impossible. The '
                'hazardous conditions could impact the morning commute.'
            ),
        )
        self._add_nws_alert(
            profile,
            event_code = 'TOA',
            event_name = 'Tornado Watch',
            severity = 'Severe', certainty = 'Possible', urgency = 'Future',
            category = 'met', area_desc = area,
            headline = 'Tornado Watch in effect for Demo County',
            description = (
                'Conditions are favorable for the development of '
                'tornadoes within the watch area. Damaging winds and '
                'large hail are also possible.'
            ),
            instruction = (
                'Review tornado safety rules and be prepared to take '
                'shelter quickly if a warning is issued.'
            ),
        )
        self._add_nws_alert(
            profile,
            event_code = '',
            event_name = 'Heat Advisory',
            severity = 'Moderate', certainty = 'Likely', urgency = 'Expected',
            category = 'met', area_desc = area,
            headline = 'Heat Advisory in effect for Demo County',
            description = (
                'Heat index values up to 105 expected. Hot temperatures '
                'and high humidity may cause heat illnesses to occur.'
            ),
            instruction = (
                'Drink plenty of fluids, stay in an air-conditioned '
                'room, and check up on relatives and neighbors.'
            ),
        )
        self._add_nws_alert(
            profile,
            event_code = 'AQA',
            event_name = 'Air Quality Alert',
            severity = 'Moderate', certainty = 'Observed', urgency = 'Expected',
            category = 'health', area_desc = area,
            headline = 'Air Quality Alert for Demo County',
            description = (
                'The Department of Environmental Quality has issued an '
                'Air Quality Alert. Fine particulate concentrations are '
                'expected to reach unhealthy levels.'
            ),
            instruction = (
                'Sensitive groups including children, the elderly, and '
                'those with heart or lung conditions should limit '
                'prolonged outdoor exertion.'
            ),
        )
        return profile.nws_sim_alerts.count()

    # ----- per-integration row builders -----

    def _add_hass_light_switch(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            fields_class = HassInsteonLightSwitchFields,
            sim_entity_type = SimEntityType.LIGHT,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_dimmer(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            fields_class = HassInsteonDimmerLightSwitchFields,
            sim_entity_type = SimEntityType.LIGHT,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_dual_band(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            fields_class = HassInsteonDualBandLightSwitchFields,
            sim_entity_type = SimEntityType.LIGHT,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_motion(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            fields_class = HassInsteonMotionDetectorFields,
            sim_entity_type = SimEntityType.MOTION_SENSOR,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_open_close(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            fields_class = HassInsteonOpenCloseSensorFields,
            sim_entity_type = SimEntityType.OPEN_CLOSE_SENSOR,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_outlet(self, profile, name, addr):
        self._create_db_entity(
            profile = profile,
            fields_class = HassInsteonOutletFields,
            sim_entity_type = SimEntityType.ELECTRICAL_OUTLET,
            fields_kwargs = {'name': name, 'insteon_address': addr},
        )

    def _add_hass_smart_bulb(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassSmartBulbFields,
            sim_entity_type = SimEntityType.LIGHT,
            fields_kwargs = {'name': name},
        )

    def _add_hass_color_smart_bulb(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassColorSmartBulbFields,
            sim_entity_type = SimEntityType.LIGHT,
            fields_kwargs = {'name': name},
        )

    def _add_hass_door_contact(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassDoorContactSensorFields,
            sim_entity_type = SimEntityType.OPEN_CLOSE_SENSOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_window_contact(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassWindowContactSensorFields,
            sim_entity_type = SimEntityType.OPEN_CLOSE_SENSOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_smoke_detector(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassSmokeDetectorFields,
            sim_entity_type = SimEntityType.SMOKE_DETECTOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_smoke_detector_with_battery(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassSmokeDetectorWithBatteryFields,
            sim_entity_type = SimEntityType.SMOKE_DETECTOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_carbon_monoxide_detector(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassCarbonMonoxideDetectorFields,
            sim_entity_type = SimEntityType.CARBON_MONOXIDE_DETECTOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_gas_detector(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassGasDetectorFields,
            sim_entity_type = SimEntityType.GAS_DETECTOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_motion_sensor(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassMotionSensorFields,
            sim_entity_type = SimEntityType.MOTION_SENSOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_combo_motion_sensor(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassComboMotionSensorFields,
            sim_entity_type = SimEntityType.MOTION_SENSOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_presence_sensor(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassPresenceSensorFields,
            sim_entity_type = SimEntityType.PRESENCE_SENSOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_opening_sensor(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassOpeningSensorFields,
            sim_entity_type = SimEntityType.OPEN_CLOSE_SENSOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_power_meter(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassPowerMeterFields,
            sim_entity_type = SimEntityType.ELECTRICY_METER,
            fields_kwargs = {'name': name},
        )

    def _add_hass_weather_station(self, profile, name, temperature_unit = '°F'):
        self._create_db_entity(
            profile = profile,
            fields_class = HassWeatherStationFields,
            sim_entity_type = SimEntityType.BAROMETER,
            fields_kwargs = {
                'name': name,
                'temperature_unit': temperature_unit,
            },
        )

    def _add_hass_occupancy_light_sensor(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassOccupancyLightSensorFields,
            sim_entity_type = SimEntityType.PRESENCE_SENSOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_water_leak_sensor(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassWaterLeakSensorFields,
            sim_entity_type = SimEntityType.LEAK_SENSOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_switch(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassSwitchFields,
            sim_entity_type = SimEntityType.WALL_SWITCH,
            fields_kwargs = {'name': name},
        )

    def _add_hass_camera(self, profile, name, entity_id_suffix):
        self._create_db_entity(
            profile = profile,
            fields_class = HassCameraSimEntityFields,
            sim_entity_type = SimEntityType.CAMERA,
            fields_kwargs = {
                'name': name,
                'entity_id_suffix': entity_id_suffix,
            },
        )

    def _add_hass_camera_no_motion(self, profile, name, entity_id_suffix):
        self._create_db_entity(
            profile = profile,
            fields_class = HassCameraNoMotionSimEntityFields,
            sim_entity_type = SimEntityType.CAMERA,
            fields_kwargs = {
                'name': name,
                'entity_id_suffix': entity_id_suffix,
            },
        )

    def _add_hass_basic_outlet(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassOutletFields,
            sim_entity_type = SimEntityType.ELECTRICAL_OUTLET,
            fields_kwargs = {'name': name},
        )

    def _add_hass_temperature_sensor(self, profile, name, temperature_unit = '°F'):
        self._create_db_entity(
            profile = profile,
            fields_class = HassTemperatureSensorFields,
            sim_entity_type = SimEntityType.THERMOMETER,
            fields_kwargs = {
                'name': name,
                'temperature_unit': temperature_unit,
            },
        )

    def _add_hass_humidity_sensor(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassHumiditySensorFields,
            sim_entity_type = SimEntityType.HYGROMETER,
            fields_kwargs = {'name': name},
        )

    def _add_hass_temp_humidity_sensor(self, profile, name, temperature_unit = '°F'):
        self._create_db_entity(
            profile = profile,
            fields_class = HassTempHumiditySensorFields,
            sim_entity_type = SimEntityType.THERMOMETER,
            fields_kwargs = {
                'name': name,
                'temperature_unit': temperature_unit,
            },
        )

    def _add_hass_lock(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassLockFields,
            sim_entity_type = SimEntityType.DOOR_LOCK,
            fields_kwargs = {'name': name},
        )

    def _add_hass_garage_cover(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassGarageCoverFields,
            sim_entity_type = SimEntityType.OPEN_CLOSE_ACTUATOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_window_blind_cover(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassWindowBlindCoverFields,
            sim_entity_type = SimEntityType.OPEN_CLOSE_ACTUATOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_generic_cover(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassGenericCoverFields,
            sim_entity_type = SimEntityType.OPEN_CLOSE_ACTUATOR,
            fields_kwargs = {'name': name},
        )

    def _add_hass_ceiling_fan(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassFanFields,
            sim_entity_type = SimEntityType.CEILING_FAN,
            fields_kwargs = {'name': name},
        )

    def _add_hass_multi_feature_fan(self, profile, name):
        self._create_db_entity(
            profile = profile,
            fields_class = HassMultiFeatureFanFields,
            sim_entity_type = SimEntityType.CEILING_FAN,
            fields_kwargs = {'name': name},
        )

    def _add_hass_thermostat(self, profile, name,
                             hvac_modes=None, fan_modes=None,
                             temperature_unit='°F'):
        fields_kwargs = {
            'name': name,
            'temperature_unit': temperature_unit,
        }
        if hvac_modes is not None:
            fields_kwargs[ 'hvac_modes' ] = hvac_modes
        if fan_modes is not None:
            fields_kwargs[ 'fan_modes' ] = fan_modes
        self._create_db_entity(
            profile = profile,
            fields_class = HassThermostatFields,
            sim_entity_type = SimEntityType.THERMOSTAT,
            fields_kwargs = fields_kwargs,
        )

    def _add_homebox_item(self, profile, name, **fields_kwargs):
        kwargs = {'name': name}
        kwargs.update(fields_kwargs)
        self._create_db_entity(
            profile = profile,
            fields_class = HomeBoxInventoryItemFields,
            sim_entity_type = SimEntityType.OTHER,
            fields_kwargs = kwargs,
        )

    def _add_zm_server(self, profile):
        self._create_db_entity(
            profile = profile,
            fields_class = ZmServerSimEntityFields,
            sim_entity_type = SimEntityType.SERVICE,
            fields_kwargs = {'name': 'ZM Server'},
        )

    def _add_zm_monitor(self, profile, name, monitor_id):
        self._create_db_entity(
            profile = profile,
            fields_class = ZmMonitorSimEntityFields,
            sim_entity_type = SimEntityType.MOTION_SENSOR,
            fields_kwargs = {'name': name, 'monitor_id': monitor_id},
        )

    def _add_frigate_camera(self, profile, name, camera_name):
        self._create_db_entity(
            profile = profile,
            fields_class = FrigateCameraSimEntityFields,
            sim_entity_type = SimEntityType.CAMERA,
            fields_kwargs = {'name': name, 'camera_name': camera_name},
        )

    def _add_nws_alert(self, profile, *,
                       event_code, event_name,
                       severity, certainty, urgency, category,
                       area_desc, headline, description, instruction,
                       status = 'Actual',
                       effective_offset_secs = -3600,
                       expires_offset_secs = 43200):
        NwsSimAlert.objects.create(
            sim_profile = profile,
            is_active = False,
            event_code = event_code,
            event_name = event_name,
            severity_str = severity,
            certainty_str = certainty,
            urgency_str = urgency,
            status_str = status,
            category_str = category,
            headline = headline,
            description = description,
            instruction = instruction,
            area_desc = area_desc,
            effective_offset_secs = effective_offset_secs,
            expires_offset_secs = expires_offset_secs,
        )

    # ----- low-level row creator -----

    def _create_db_entity(self,
                          profile: SimProfile,
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
            entity_fields_class_id = fields_class.class_id(),
            sim_entity_type_str = str(sim_entity_type),
            sim_entity_fields_json = fields_instance.to_json_dict(),
        )
