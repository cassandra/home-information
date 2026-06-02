"""Per-module current-profile state for the simulator.

Singleton. Each module (`module_key`) has its own ``current`` profile.
Switching one module's profile does not affect any other module.
Hydrates lazily — first access for a module reads the DB; if the
module has no profiles, an ``empty`` profile is created.
"""
import logging
import threading
from typing import Dict, List, Optional

from django.db import transaction

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton

from .models import SimProfile

logger = logging.getLogger(__name__)


EMPTY_PROFILE_NAME = 'empty'


class ProfileManager( Singleton ):

    def __init_singleton__(self):
        self._current_by_module : Dict[ str, SimProfile ] = {}
        self._lock = threading.Lock()
        self._on_switched_callbacks : Dict[ str, list ] = {}
        return

    def list_profiles( self, module_key : str ) -> List[ SimProfile ]:
        return list( SimProfile.objects
                     .filter( module_key = module_key )
                     .order_by( 'name' ))

    def get_current( self, module_key : str ) -> SimProfile:
        with self._lock:
            cached = self._current_by_module.get( module_key )
            if cached is not None:
                # Re-fetch to pick up edits to the row (e.g. rename).
                try:
                    return SimProfile.objects.get( pk = cached.pk )
                except SimProfile.DoesNotExist:
                    # Cached entry was deleted out from under us; fall
                    # through to re-pick from DB.
                    self._current_by_module.pop( module_key, None )

            profile = self._pick_current_from_db( module_key )
            if profile is None:
                profile = self._auto_create_empty( module_key )
            self._current_by_module[ module_key ] = profile
            return profile

    def set_current( self, module_key : str, profile : SimProfile ) -> SimProfile:
        if profile.module_key != module_key:
            raise ValueError(
                f'Profile {profile.pk} belongs to module {profile.module_key!r},'
                f' not {module_key!r}.'
            )
        with transaction.atomic():
            profile.last_switched_to_datetime = datetimeproxy.now()
            profile.save( update_fields = [ 'last_switched_to_datetime' ] )
        with self._lock:
            self._current_by_module[ module_key ] = profile
        self._dispatch_switched( module_key, profile )
        return profile

    def create( self, module_key : str, name : str ) -> SimProfile:
        profile = SimProfile.objects.create(
            module_key = module_key,
            name = name,
        )
        return profile

    def clone( self,
               module_key : str,
               source_profile : SimProfile,
               new_name : str ) -> SimProfile:
        if source_profile.module_key != module_key:
            raise ValueError(
                f'Source profile module mismatch: {source_profile.module_key!r}'
                f' vs {module_key!r}.'
            )
        with transaction.atomic():
            new_profile = SimProfile.objects.create(
                module_key = module_key,
                name = new_name,
            )
            self._copy_owned_rows(
                source_profile = source_profile,
                target_profile = new_profile,
            )
        return new_profile

    def delete( self, module_key : str, profile : SimProfile ) -> None:
        if profile.module_key != module_key:
            raise ValueError( 'Profile module mismatch on delete.' )
        with self._lock:
            cached = self._current_by_module.get( module_key )
            if cached is not None and cached.pk == profile.pk:
                self._current_by_module.pop( module_key, None )
        profile.delete()
        # Force re-pick of current on next get_current(); also fires the
        # switched callback so the module reloads against the new current.
        new_current = self.get_current( module_key )
        self._dispatch_switched( module_key, new_current )
        return

    def register_on_switched( self, module_key : str, callback ):
        """Module registers a callback invoked after every
        set_current / delete-driven switch for that module_key.
        Callback signature: ``callback(profile: SimProfile)``."""
        self._on_switched_callbacks.setdefault( module_key, [] ).append( callback )
        return

    def _pick_current_from_db( self, module_key : str ) -> Optional[ SimProfile ]:
        return ( SimProfile.objects
                 .filter( module_key = module_key )
                 .order_by( '-last_switched_to_datetime', 'name' )
                 .first() )

    def _auto_create_empty( self, module_key : str ) -> SimProfile:
        profile, _created = SimProfile.objects.get_or_create(
            module_key = module_key,
            name = EMPTY_PROFILE_NAME,
        )
        return profile

    def _dispatch_switched( self, module_key : str, profile : SimProfile ):
        for callback in self._on_switched_callbacks.get( module_key, () ):
            try:
                callback( profile )
            except Exception:
                logger.exception(
                    f'Profile-switched callback failed for {module_key!r}'
                )
            continue
        return

    def _copy_owned_rows( self,
                          source_profile : SimProfile,
                          target_profile : SimProfile ) -> None:
        """Profile rows referencing source via FK get duplicates pointing
        at target. Each owning sub-app is responsible for handling its
        own clone via on_profile_cloned callback (future). For now,
        copy DbSimEntity (services), NwsSimAlert (nws), and the
        single-row astronomical state models by import."""
        # Imports kept local — these are cross-sub-app references and
        # we want lazy resolution so the profile sub-app remains
        # importable in isolation (e.g. management commands that touch
        # only profiles).
        from hi.simulator.services.models import DbSimEntity
        from hi.simulator.weather_sources.nws.models import NwsSimAlert, NwsSimConditions
        from hi.simulator.weather_sources.openmeteo.models import OpenMeteoSimState
        from hi.simulator.weather_sources.sunrise_sunset_org.models import (
            SunriseSunsetSimState,
        )
        from hi.simulator.weather_sources.usno.models import UsnoSimState

        DbSimEntity.objects.bulk_create([
            DbSimEntity(
                sim_profile = target_profile,
                entity_fields_class_id = row.entity_fields_class_id,
                sim_entity_type_str = row.sim_entity_type_str,
                sim_entity_fields_json = row.sim_entity_fields_json,
            )
            for row in source_profile.db_sim_entities.all()
        ])
        NwsSimAlert.objects.bulk_create([
            NwsSimAlert(
                sim_profile = target_profile,
                is_active = row.is_active,
                event_code = row.event_code,
                event_name = row.event_name,
                severity_str = row.severity_str,
                certainty_str = row.certainty_str,
                urgency_str = row.urgency_str,
                status_str = row.status_str,
                category_str = row.category_str,
                headline = row.headline,
                description = row.description,
                instruction = row.instruction,
                area_desc = row.area_desc,
                effective_offset_secs = row.effective_offset_secs,
                expires_offset_secs = row.expires_offset_secs,
            )
            for row in source_profile.nws_sim_alerts.all()
        ])

        # OneToOne single-row state models: copy if the source profile
        # has one. ``hasattr`` guards the RelatedObjectDoesNotExist that
        # the reverse accessor raises when no row exists yet.
        if hasattr( source_profile, 'sunrise_sunset_sim_state' ):
            src = source_profile.sunrise_sunset_sim_state
            SunriseSunsetSimState.objects.create(
                sim_profile = target_profile,
                sunrise = src.sunrise,
                sunset = src.sunset,
                solar_noon = src.solar_noon,
                utc_offset_hours = src.utc_offset_hours,
                status_str = src.status_str,
            )
        if hasattr( source_profile, 'usno_sim_state' ):
            src = source_profile.usno_sim_state
            UsnoSimState.objects.create(
                sim_profile = target_profile,
                sunrise = src.sunrise,
                sunset = src.sunset,
                solar_noon = src.solar_noon,
                moonrise = src.moonrise,
                moonset = src.moonset,
                fracillum_percent = src.fracillum_percent,
                curphase_str = src.curphase_str,
                tz_offset_hours = src.tz_offset_hours,
            )
        if hasattr( source_profile, 'nws_sim_conditions' ):
            src = source_profile.nws_sim_conditions
            NwsSimConditions.objects.create(
                sim_profile = target_profile,
                text_description = src.text_description,
                temperature_c = src.temperature_c,
                dewpoint_c = src.dewpoint_c,
                relative_humidity_pct = src.relative_humidity_pct,
                wind_speed_kmh = src.wind_speed_kmh,
                wind_direction_deg = src.wind_direction_deg,
                barometric_pressure_hpa = src.barometric_pressure_hpa,
                cloud_amount = src.cloud_amount,
                precip_probability_pct = src.precip_probability_pct,
                is_daytime = src.is_daytime,
            )
        if hasattr( source_profile, 'openmeteo_sim_state' ):
            src = source_profile.openmeteo_sim_state
            OpenMeteoSimState.objects.create(
                sim_profile = target_profile,
                temperature_c = src.temperature_c,
                temperature_min_c = src.temperature_min_c,
                relative_humidity_pct = src.relative_humidity_pct,
                dewpoint_c = src.dewpoint_c,
                precipitation_mm = src.precipitation_mm,
                pressure_msl_hpa = src.pressure_msl_hpa,
                windspeed_kmh = src.windspeed_kmh,
                winddirection_deg = src.winddirection_deg,
                weathercode = src.weathercode,
                is_day = src.is_day,
            )
        return
