"""Paperless-ngx simulator views.

Three endpoint families:

  - ``DocumentsListView`` — the parametric search endpoint. The
    integration's referencer hits this for every search. Response
    shape mirrors the real paperless ``GET /api/documents/?query=q``
    (DRF pagination envelope + per-doc dict).

  - ``ThumbnailView`` and ``PreviewView`` — mirror real paperless's
    per-document endpoints so the picker's thumbnail / source-URL
    handling can be exercised. ``ThumbnailView`` 404s when the
    operator has thumbnails turned off so the picker's fallback-icon
    path runs.

  - ``SetSettingsView`` — POST target for the extras form. Mutates
    the singleton's PaperlessSimSettings and re-renders the form
    fragment (the form posts via antinode ``data-async`` so the
    extras pane swaps in place).
"""
import hashlib
import random
import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import List, Optional

from django.core.exceptions import BadRequest
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View

from .simulator import (
    MimeMix,
    PaperlessSimSettings,
    PaperlessSimulator,
    RESULT_COUNT_CHOICES,
)


# ---- generator ---------------------------------------------------


_MIME_PALETTE = {
    MimeMix.PDF_ONLY: ( 'application/pdf', ),
    MimeMix.IMAGE_ONLY: ( 'image/png', 'image/jpeg' ),
    MimeMix.TEXT_ONLY: ( 'text/plain', ),
    MimeMix.MIXED: ( 'application/pdf', 'image/png', 'text/plain' ),
}

_EXTENSION_BY_MIME = {
    'application/pdf' : 'pdf',
    'image/png'       : 'png',
    'image/jpeg'      : 'jpg',
    'text/plain'      : 'txt',
}

# Filler phrases for synthetic snippets. The query is interleaved so
# the picker's snippet rendering carries a visible breadcrumb of the
# search input.
_SNIPPET_FRAGMENTS = (
    'Annual maintenance record for {query} including replacement schedule.',
    'Warranty terms for {query}; refer to section 4 for exclusions.',
    'Installation manual for the {query} unit. Calibration steps follow.',
    'Service receipt covering parts and labor on the {query} repair.',
    'Compliance certificate issued for the {query} system this cycle.',
)


def _stable_document_id( query : str, index : int ) -> int:
    """Map (query, index) to a stable, distinct, positive document
    id. Different queries produce distinct ids; the same query
    repeated yields the same ids. Real paperless uses unbounded
    integer document ids, so a 7-hex-digit hash (~268M range) is a
    safe stand-in."""
    digest = hashlib.sha256( f'{query}\x00{index}'.encode() ).hexdigest()
    return int( digest[:7], 16 )


def _pick_mime( mix : MimeMix, index : int ) -> str:
    """Deterministic per-index mime pick. Cycles through the palette
    so a multi-result page rendered with MIXED visits each type."""
    palette = _MIME_PALETTE[ mix ]
    return palette[ index % len(palette) ]


def _generate_results(
        settings : PaperlessSimSettings, query : str,
) -> List[dict]:
    """Build ``settings.result_count`` synthetic paperless documents
    for the given query. RNG is seeded from the query so a repeated
    search returns the same set — predictable for the operator."""
    rng = random.Random( query or '' )
    now_iso = datetime.now(timezone.utc).isoformat()
    documents = []
    for index in range( settings.result_count ):
        mime_type = _pick_mime( settings.mime_mix, index )
        extension = _EXTENSION_BY_MIME[ mime_type ]
        # Document id is derived from (query, index) so different
        # queries produce distinct ids — the picker uses the resulting
        # source URL as the per-result identity, and repeating ids
        # across queries would make the picker think different docs
        # were the same. (query, index) repeats stay stable, matching
        # real paperless's "same document re-found in multiple
        # searches" behavior.
        document_id = _stable_document_id( query or '', index )
        content = (
            rng.choice( _SNIPPET_FRAGMENTS ).format( query = query or 'document' )
            if settings.snippets else ''
        )
        # Titles use a human-readable index, not the hashed id, so
        # operators see "Result 1, Result 2, ..." regardless of
        # whatever id the URL ends up with.
        title = f'{query or "document"} — Result {index + 1}'
        documents.append({
            'id'                  : document_id,
            'correspondent'       : None,
            'document_type'       : None,
            'storage_path'        : None,
            'title'               : title,
            'content'             : content,
            'tags'                : [],
            'created'             : now_iso,
            'modified'            : now_iso,
            'added'               : now_iso,
            'archive_serial_number': None,
            'original_file_name'  : f'doc-{index + 1}.{extension}',
            'archived_file_name'  : None,
            'mime_type'           : mime_type,
            'is_shared_by_requester': False,
            'notes'               : [],
            'custom_fields'       : [],
        })
    return documents


# ---- endpoints ---------------------------------------------------


class DocumentsListView( View ):
    """``GET /api/documents/?query=...`` — paginated documents
    search, matching paperless-ngx's response envelope."""

    def get( self, request, *args, **kwargs ):
        simulator = PaperlessSimulator()
        settings = simulator.settings
        if settings.latency_ms > 0:
            time.sleep( settings.latency_ms / 1000.0 )
        query = request.GET.get( 'query', '' ).strip()
        results = _generate_results( settings, query )
        # Mirrors the DRF pagination envelope the real paperless
        # API uses — single page, no next/previous.
        return JsonResponse({
            'count'    : len( results ),
            'next'     : None,
            'previous' : None,
            'all'      : [ r['id'] for r in results ],
            'results'  : results,
        })


def _thumbnail_svg( document_id : int ) -> bytes:
    """Tiny SVG placeholder. Avoids shipping a binary thumbnail just
    so the picker can render *something* in the thumbnail slot."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="160" '
        f'viewBox="0 0 120 160">'
        f'<rect width="120" height="160" fill="#e9ecef" stroke="#adb5bd"/>'
        f'<text x="60" y="86" text-anchor="middle" font-family="sans-serif" '
        f'font-size="20" fill="#495057">#{document_id}</text>'
        f'</svg>'
    ).encode('utf-8')


class ThumbnailView( View ):
    """``GET /api/documents/<id>/thumb/`` — serves an SVG placeholder
    when thumbnails are enabled; 404s otherwise so the picker's
    fallback-icon path can be exercised."""

    def get( self, request, *args, **kwargs ):
        simulator = PaperlessSimulator()
        if not simulator.settings.thumbnails:
            return HttpResponse( status = 404 )
        try:
            document_id = int( kwargs.get( 'document_id' ) )
        except (TypeError, ValueError):
            return HttpResponse( status = 404 )
        return HttpResponse(
            _thumbnail_svg( document_id ),
            content_type = 'image/svg+xml',
        )


class PreviewView( View ):
    """``GET /documents/<id>/details/`` — minimal preview page
    representing the per-document view in paperless's web UI. The
    picker links here as the result's source URL."""

    TEMPLATE_NAME = 'paperless/pages/document_preview.html'

    def get( self, request, *args, **kwargs ):
        try:
            document_id = int( kwargs.get( 'document_id' ) )
        except (TypeError, ValueError):
            return HttpResponse( status = 404 )
        return render(
            request,
            self.TEMPLATE_NAME,
            { 'document_id': document_id },
        )


class SetSettingsView( View ):
    """POST target for the extras form. Validates each field,
    updates the singleton, and re-renders the settings fragment."""

    TEMPLATE_NAME = 'paperless/panes/settings_form.html'

    def post( self, request, *args, **kwargs ):
        simulator = PaperlessSimulator()
        current = simulator.settings
        new_settings = replace(
            current,
            result_count = self._parse_result_count(
                request.POST.get( 'result_count' ), current.result_count,
            ),
            mime_mix = self._parse_mime_mix(
                request.POST.get( 'mime_mix' ),
            ),
            thumbnails = self._parse_bool(
                request.POST.get( 'thumbnails' ),
            ),
            snippets = self._parse_bool(
                request.POST.get( 'snippets' ),
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

    @staticmethod
    def _parse_latency_ms( raw : Optional[str], fallback : int ) -> int:
        try:
            value = int( raw )
        except (TypeError, ValueError):
            return fallback
        if value < 0 or value > 10000:
            raise BadRequest( f'latency_ms out of range: {raw!r}' )
        return value
