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
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from typing import List, Optional

from django.core.exceptions import BadRequest
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from PIL import Image, ImageDraw

from .simulator import (
    ImmichSimSettings,
    ImmichSimulator,
    MimeMix,
    RESULT_COUNT_CHOICES,
)


# ---- asset generator --------------------------------------------


_CITY_COUNTRY_CYCLE = (
    ( 'Portland', 'USA' ),
    ( 'Seattle', 'USA' ),
    ( 'Vancouver', 'Canada' ),
    ( None, None ),  # exercise the no-EXIF row
)

# Per-mime-mix palette of (mime_type, asset_type, file_extension).
# IMAGE assets cycle through real-world Immich image formats; VIDEO
# assets are mp4 (the most common). MIXED alternates per index so a
# single result page surfaces both card types.
_MIME_PALETTE = {
    MimeMix.IMAGE_ONLY: (
        ( 'image/jpeg', 'IMAGE', 'jpg' ),
        ( 'image/png', 'IMAGE', 'png' ),
    ),
    MimeMix.VIDEO_ONLY: (
        ( 'video/mp4', 'VIDEO', 'mp4' ),
    ),
    MimeMix.MIXED: (
        ( 'image/jpeg', 'IMAGE', 'jpg' ),
        ( 'video/mp4', 'VIDEO', 'mp4' ),
        ( 'image/png', 'IMAGE', 'png' ),
    ),
}


def _stable_asset_id( query : str, index : int ) -> str:
    """Map (query, index) to a stable UUID-shaped string. Different
    queries produce distinct ids; same query -> same ids."""
    digest = hashlib.sha256( f'{query}\x00{index}'.encode() ).hexdigest()
    # UUID v4 layout: 8-4-4-4-12 hex. Borrow the first 32 digest chars.
    return (
        f'{digest[0:8]}-{digest[8:12]}-{digest[12:16]}-'
        f'{digest[16:20]}-{digest[20:32]}'
    )


def _pick_mime( mix : MimeMix, index : int ):
    """Deterministic per-index palette pick. Cycles through the
    palette so a multi-result page rendered with MIXED visits each
    type. Returns ``(mime_type, asset_type, file_extension)``."""
    palette = _MIME_PALETTE[ mix ]
    return palette[ index % len(palette) ]


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
        mime_type, asset_type, extension = _pick_mime(
            settings.mime_mix, index,
        )
        # Filename bakes in the query so operators can visually trace
        # what was searched.
        stem = (query or "asset").strip().replace(" ", "-")
        filename = f'{stem}-{index + 1}.{extension}'
        asset = {
            'id'                : asset_id,
            'originalFileName'  : filename,
            'originalMimeType'  : mime_type,
            'type'              : asset_type,
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


def _thumbnail_png( asset_id : str ) -> bytes:
    """Tiny PNG placeholder generated with Pillow. Real Immich
    returns a raster image from this endpoint; matching that lets
    the framework's attach-time bytes-to-file write produce a file
    the browser can later decode (the manager hard-codes the saved
    filename's extension to ``.png``)."""
    short = asset_id.split('-')[0] if asset_id else 'asset'
    img = Image.new( 'RGB', ( 160, 160 ), ( 207, 226, 255 ))
    draw = ImageDraw.Draw( img )
    text_box = draw.textbbox( ( 0, 0 ), short )
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]
    draw.text(
        ( (160 - text_w) // 2, (160 - text_h) // 2 ),
        short, fill = ( 8, 66, 152 ),
    )
    buf = BytesIO()
    img.save( buf, format = 'PNG' )
    return buf.getvalue()


class ThumbnailView( View ):
    """``GET /api/assets/<id>/thumbnail`` -- serves a PNG placeholder
    when thumbnails are enabled; 404s otherwise so HI's no-thumbnail
    fallback can be exercised."""

    def get( self, request, *args, **kwargs ):
        simulator = ImmichSimulator()
        if not simulator.settings.thumbnails:
            return HttpResponse( status = 404 )
        asset_id = kwargs.get( 'asset_id' ) or ''
        return HttpResponse(
            _thumbnail_png( asset_id ),
            content_type = 'image/png',
        )


def _original_png( asset_id : str ) -> bytes:
    """Real PNG bytes for the original-asset endpoint. Larger than
    the thumbnail placeholder and orange-tinted so a HI-generated
    thumbnail produced from these bytes is visually distinguishable
    from the blue upstream thumbnail when the operator toggles
    ``thumbnails`` off to exercise the fallback path."""
    short = asset_id.split('-')[0] if asset_id else 'asset'
    img = Image.new( 'RGB', ( 640, 480 ), ( 255, 224, 178 ))
    draw = ImageDraw.Draw( img )
    label = f'original\n{short}'
    text_box = draw.multiline_textbbox( ( 0, 0 ), label )
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]
    draw.multiline_text(
        ( (640 - text_w) // 2, (480 - text_h) // 2 ),
        label, fill = ( 230, 81, 0 ), align = 'center',
    )
    buf = BytesIO()
    img.save( buf, format = 'PNG' )
    return buf.getvalue()


class OriginalView( View ):
    """``GET /api/assets/<id>/original`` -- always-on PNG. HI's
    referencer hits this as the defensive fallback when the
    thumbnail endpoint is unavailable; serving real bytes here lets
    operators exercise the HI-generated thumbnail path (turn
    ``thumbnails`` off, attach an image asset, see a HI-generated
    thumbnail on the saved card)."""

    def get( self, request, *args, **kwargs ):
        asset_id = kwargs.get( 'asset_id' ) or ''
        return HttpResponse(
            _original_png( asset_id ),
            content_type = 'image/png',
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
            mime_mix = self._parse_mime_mix(
                request.POST.get( 'mime_mix' ),
            ),
            include_exif = self._parse_bool(
                request.POST.get( 'include_exif' ),
            ),
            thumbnails = self._parse_bool(
                request.POST.get( 'thumbnails' ),
            ),
        )
        simulator.set_settings( new_settings )
        return render(
            request,
            self.TEMPLATE_NAME,
            {
                'settings'             : new_settings,
                'result_count_choices' : RESULT_COUNT_CHOICES,
                'mime_mix_choices'     : list( MimeMix ),
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
    def _parse_mime_mix( raw : Optional[str] ) -> MimeMix:
        try:
            return MimeMix[ raw ]
        except (KeyError, TypeError):
            raise BadRequest( f'Invalid mime_mix: {raw!r}' )

    @staticmethod
    def _parse_bool( raw : Optional[str] ) -> bool:
        # An unchecked checkbox is absent from the POST body, so the
        # mere presence of the field name (with any truthy value) is
        # the signal.
        return bool( raw )


# ---- helpers ----------------------------------------------------


def _safe_json( body : bytes ) -> dict:
    if not body:
        return {}
    return json.loads( body.decode('utf-8') )
