"""
External-data view models for the entity-detail modal.

An integration's gateway returns an ``ExternalViewData`` subclass
instance from ``get_external_view_data(entity)`` to render the
external-data view region of the modal; returning ``None`` suppresses
that region entirely. ``template_name`` is a class-level attribute on
each subclass pointing at the partial that renders it; integrations
can provide their own subclass with a custom ``template_name`` for
fully bespoke layouts.

Default partials live under
``hi/integrations/templates/integrations/external_data/entity/``.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class NameValuePair:
    """A single named value for display in a ``StructuredViewData``
    attribute list. Order is determined by list position."""
    name: str
    value: str


@dataclass
class AttachmentRef:
    """A reference to an externally-hosted attachment for display in a
    ``StructuredViewData`` attachment grid. The integration is
    responsible for providing a working ``thumbnail_url`` and
    ``open_url`` (which may point at HI proxy endpoints for auth-gated
    upstreams)."""
    id: str
    title: str
    mime_type: str
    thumbnail_url: Optional[str] = None
    open_url: Optional[str] = None


@dataclass
class ExternalViewData:
    """Base for external-data view payloads. Subclasses set
    ``template_name`` to the partial that renders them."""

    template_name: str = ''
    deep_link_url: Optional[str] = None


@dataclass
class StructuredViewData(ExternalViewData):
    """Common case: name/value rows plus a grid of attachments."""

    template_name: str = 'integrations/external_data/entity/structured.html'
    attributes: List[NameValuePair] = field(default_factory=list)
    attachments: List[AttachmentRef] = field(default_factory=list)


@dataclass
class CustomTemplateViewData(ExternalViewData):
    """Escape hatch for integrations needing a fully custom layout.
    The integration sets ``template_name`` to a path under its own
    ``services/<name>/templates/...`` and supplies whatever
    ``context`` it needs."""

    template_name: str = ''
    context: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.template_name or not self.template_name.strip():
            raise ValueError(
                'CustomTemplateViewData requires a non-empty template_name.'
            )


@dataclass
class MinimalViewData(ExternalViewData):
    """Placeholder when a full view payload is unavailable. Renders the
    deep link and the optional ``error_message``."""

    template_name: str = 'integrations/external_data/entity/minimal.html'
    error_message: Optional[str] = None
