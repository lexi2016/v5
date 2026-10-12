# M06 fixed-source integration request to the existing P0 writer

No shared source, gateway, UI, route configuration, scheduler or generation is modified by this delivery.

## Runtime boundary

Run M06 from its private source root, handoffs/M06/source, in a cold Python process with that root's V5/src on the import path. Do not import its private v5_shadow helpers over a long-lived P0 process. Its duplicate helper copies are read-only source dependencies, not replacement patches for shared files.

Use produce_hk02_daily for an explicitly authorized bounded attempt. Store its returned committed_reference and ledger_run_id. Preserve the exact computation identities, trigger mode, fixture flag and business status. For read-only views, use read_verified_hk_preselection_reference, never a producer function, mutable latest pointer, synthetic successful dictionary or fallback from another date.

## Existing module-response record

The pure project_hk_preselection_record(bound_root, reference, *, config, path, query) helper requires an already verified runtime config with module_id, release_id and routes. The caller supplies the actual existing route and query; this module does not invent a route or port. It independently reads the exact committed reference and returns the unchanged v5.module_response.v1 shape validated by the original _validate_record:

schema_version, module_id, release_id, path, query, payload, payload_sha256, source_input_sha256, data_kind, generated_at, status_code.

The payload carries the full artifact and committed reference. Synthetic source is marked SYNTHETIC; genuine owner-result source may be OWNER_RESULT. SOURCE_SNAPSHOT is an input-admission label, not a new shared API enum. The helper is read-only and performs no generation or publication.

P0 may pass that record to its existing publish_generation(config, records, expected_generation=...) CAS only in its authorized single-writer window, after actual runtime config/route identity is inspected. Preserve every unrelated record and the previous generation for rollback. No shared enum or guard relaxation is requested.

## Required integration checks

- Same target/signal/eligibility/cutoff and exact source run/artifact/manifest/receipt in consumer, committed reference, M08 consumer and page.
- Full 100 rows remain in the payload; pagination is presentation only.
- GET/refresh/navigation uses only reference read/projection, never model generation.
- Invalid SHA, missing or changed evidence, source qualification/PIT gaps, unsupported natural claims and wrong dates remain explicit rejection/status.
- P0 config/HTTP/generation/page/natural tests require the user's actual Mac/runtime configuration; none are claimed by this source-level package.
