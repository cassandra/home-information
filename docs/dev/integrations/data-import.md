# Data Import (IMPORT capability)

The IMPORT capability copies upstream items into HI as locally-owned
entities. Once imported, the integration has no ongoing relationship
with the upstream; HI is the source of truth.

User-facing setup lives in
[`docs/DataImport.md`](../../DataImport.md). This page is the
developer orientation — read the linked modules for the
authoritative API.

## Where the code lives

- `src/hi/integrations/importer/` — abstract `IntegrationImporter` base,
  transient models (`CandidateItem`, `IntegrationImportResult`,
  `IntegrationDiscardResult`), framework-level views (Data Import
  page, configure, preview, run, discard), templates.
- `src/hi/integrations/view_mixins.py` — `CapabilityBlockViewMixin`
  for the cross-capability block-modal detection. Mixed into both
  `ConnectorConfigureView` and `ImporterConfigureView`.
- `src/hi/services/homebox/importer/` — `HomeBoxImporter`, the first
  concrete implementation. Reference example for new IMPORT-capable
  integrations.

## How a gateway opts in

1. Add `IntegrationCapability.IMPORT` to `IntegrationMetaData.capabilities`.
2. Override `IntegrationGateway.get_importer()` to return a concrete
   `IntegrationImporter` subclass.

The `IntegrationImporter` abstract sits parallel to `IntegrationConnector`,
not inheriting from it. Commonality between Connect and Import is
composed through shared helpers (`HbEntityFactory`, `HbConverter`,
`EntityIntegrationOperations`, `PlacementUrlParams`, etc.).

## Key design decisions

- **Per-entity transaction during `run_import`.** A single item's
  failure does not abort the batch; errors are aggregated into
  `IntegrationImportResult.error_list`. See HomeBoxImporter for
  the pattern.
- **Skip-by-`integration_name`.** Imports are add-only. The framework
  view computes new-vs-skipped against existing HI entities by
  matching `integration_name`; `IntegrationImporter.get_candidate_items()`
  itself returns the full upstream list.
- **Shared `integrations_sync` exclusion lock.** Connect-side sync
  and Import-side run serialize against each other to prevent
  upstream double-fetch races on a single integration.
- **State is encoded by the integration columns alone.** An entity
  is `is_external` when `integration_id` is set (live Connect),
  `has_integration_provenance` when `previous_integration_id` is
  set (imported or detached), and neither when native. The
  `EntityModelManager` exposes named helpers (`external_for`,
  `imported_for`, `detached_for`, `with_integration_provenance`)
  for query sites; the matching `Entity` properties are
  `is_external`, `is_imported`, `is_detached`, and
  `has_integration_provenance`.

## Reference

- HomeBox concrete: `src/hi/services/homebox/importer/`
- Tests: `src/hi/integrations/tests/test_importer*.py` and
  `src/hi/services/homebox/tests/test_homebox_importer.py`.
- User-facing: [`docs/DataImport.md`](../../DataImport.md).
