"""Immich simulator views.

Endpoint families:

  - ``SmartSearchView``     -- ``POST /api/search/smart``: the smart
                              CLIP endpoint the integration's
                              referencer hits for every search. Body:
                              ``{"query": ..., "size": N}``.
  - ``MetadataSearchView``  -- ``POST /api/search/metadata``: the
                              probe-only endpoint hit by the
                              integration's ``validate_access``.
                              Returns a minimal envelope.
  - ``ThumbnailView``       -- ``GET /api/assets/<id>/thumbnail``:
                              serves an SVG placeholder.
  - ``SetSettingsView``     -- POST target for the extras form;
                              mutates the singleton's
                              ``ImmichSimSettings`` and re-renders the
                              form fragment.

Auth failures are simulated framework-wide via ``ServiceFaultMode``;
these views do not inspect the ``x-api-key`` header themselves.
"""
import hashlib
import json
import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import List, Optional

from django.core.exceptions import BadRequest
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .simulator import (
    ImmichSimSettings,
    ImmichSimulator,
    RESULT_COUNT_CHOICES,
)


# ---- asset generator --------------------------------------------


_CITY_COUNTRY_CYCLE = (
    ( 'Portland', 'USA' ),
    ( 'Seattle', 'USA' ),
    ( 'Vancouver', 'Canada' ),
    ( None, None ),  # exercise the no-EXIF row
)


def _stable_asset_id( query : str, index : int ) -> str:
    """Map (query, index) to a stable UUID-shaped string. Different
    queries produce distinct ids; same query -> same ids."""
    digest = hashlib.sha256( f'{query}\x00{index}'.encode() ).hexdigest()
    # UUID v4 layout: 8-4-4-4-12 hex. Borrow the first 32 digest chars.
    return (
        f'{digest[0:8]}-{digest[8:12]}-{digest[12:16]}-'
        f'{digest[16:20]}-{digest[20:32]}'
    )


def _generate_assets(
        settings : ImmichSimSettings, query : str,
) -> List[dict]:
    """Build ``settings.result_count`` synthetic Immich assets for the
    given query. (query, index) -> asset_id is stable so the picker
    sees the same asset on repeat searches."""
    now_iso = datetime.now(timezone.utc).isoformat()
    assets = []
    for index in range( settings.result_count ):
        asset_id = _stable_asset_id( query or '', index )
        # Filename bakes in the query so operators can visually trace
        # what was searched.
        filename = f'{(query or "asset").strip().replace(" ", "-")}-{index + 1}.jpg'
        asset = {
            'id'                : asset_id,
            'originalFileName'  : filename,
            'originalMimeType'  : 'image/jpeg',
            'type'              : 'IMAGE',
            'fileCreatedAt'     : now_iso,
        }
        if settings.include_exif:
            city, country = _CITY_COUNTRY_CYCLE[ index % len(_CITY_COUNTRY_CYCLE) ]
            asset['exifInfo'] = {
                'city': city,
                'country': country,
            }
        else:
            asset['exifInfo'] = None
        assets.append( asset )
    return assets


def _search_envelope( assets : List[dict] ) -> dict:
    return {
        'assets': {
            'items'    : assets,
            'total'    : len( assets ),
            'count'    : len( assets ),
            'nextPage' : None,
        },
        'albums': {
            'items'    : [],
            'total'    : 0,
            'count'    : 0,
            'nextPage' : None,
        },
    }


# ---- endpoints --------------------------------------------------


@method_decorator(csrf_exempt, name='dispatch')
class SmartSearchView( View ):

    def post( self, request, *args, **kwargs ):
        simulator = ImmichSimulator()
        settings = simulator.settings
        if settings.latency_ms > 0:
            time.sleep( settings.latency_ms / 1000.0 )
        # Body is JSON: {"query": "...", "size": N}. Query is read for
        # stable id generation and filename baking only; size isn't
        # honored because the operator-chosen result_count is the
        # source of truth for the simulator.
        try:
            payload = _safe_json( request.body )
        except ValueError:
            return JsonResponse({ 'message': 'Invalid JSON.' }, status = 400)
        query = ( payload.get( 'query' ) or '' ).strip()
        return JsonResponse(
            _search_envelope( _generate_assets( settings, query )),
        )


@method_decorator(csrf_exempt, name='dispatch')
class MetadataSearchView( View ):
    """Probe-only endpoint. The integration uses it for
    ``validate_access``; it never appears on the search path. Returns
    a minimal envelope."""

    def post( self, request, *args, **kwargs ):
        return JsonResponse( _search_envelope( assets = [] ))


def _thumbnail_svg( asset_id : str ) -> bytes:
    short = asset_id.split('-')[0]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" '
        f'viewBox="0 0 160 160">'
        f'<rect width="160" height="160" fill="#cfe2ff" stroke="#0d6efd"/>'
        f'<text x="80" y="86" text-anchor="middle" font-family="sans-serif" '
        f'font-size="18" fill="#084298">{short}</text>'
        f'</svg>'
    ).encode('utf-8')


class ThumbnailView( View ):

    def get( self, request, *args, **kwargs ):
        asset_id = kwargs.get( 'asset_id' ) or ''
        return HttpResponse(
            _thumbnail_svg( asset_id ),
            content_type = 'image/svg+xml',
        )


class PhotoPreviewView( View ):
    """``GET /photos/<id>`` -- minimal preview page representing the
    per-asset view in Immich's web UI. The picker links here as the
    result's persisted source URL."""

    TEMPLATE_NAME = 'immich/pages/photo_preview.html'

    def get( self, request, *args, **kwargs ):
        asset_id = kwargs.get( 'asset_id' ) or ''
        return render(
            request,
            self.TEMPLATE_NAME,
            { 'asset_id': asset_id },
        )


class SetSettingsView( View ):
    """POST target for the extras form. Validates each field, updates
    the singleton, and re-renders the settings fragment."""

    TEMPLATE_NAME = 'immich/panes/settings_form.html'

    def post( self, request, *args, **kwargs ):
        simulator = ImmichSimulator()
        current = simulator.settings
        new_settings = replace(
            current,
            result_count = self._parse_result_count(
                request.POST.get( 'result_count' ), current.result_count,
            ),
            include_exif = self._parse_bool(
                request.POST.get( 'include_exif' ),
            ),
            latency_ms = self._parse_latency_ms(
                request.POST.get( 'latency_ms' ), current.latency_ms,
            ),
        )
        simulator.set_settings( new_settings )
        return render(
            request,
            self.TEMPLATE_NAME,
            {
                'settings'             : new_settings,
                'result_count_choices' : RESULT_COUNT_CHOICES,
            },
        )

    @staticmethod
    def _parse_result_count( raw : Optional[str], fallback : int ) -> int:
        try:
            value = int( raw )
        except (TypeError, ValueError):
            return fallback
        if value not in RESULT_COUNT_CHOICES:
            raise BadRequest( f'Invalid result_count: {raw!r}' )
        return value

    @staticmethod
    def _parse_bool( raw : Optional[str] ) -> bool:
        # An unchecked checkbox is absent from the POST body, so the
        # mere presence of the field name (with any truthy value) is
        # the signal.
        return bool( raw )

    @staticmethod
    def _parse_latency_ms( raw : Optional[str], fallback : int ) -> int:
        try:
            value = int( raw )
        except (TypeError, ValueError):
            return fallback
        if value < 0 or value > 10000:
            raise BadRequest( f'latency_ms out of range: {raw!r}' )
        return value


# ---- helpers ----------------------------------------------------


def _safe_json( body : bytes ) -> dict:
    if not body:
        return {}
    return json.loads( body.decode('utf-8') )
