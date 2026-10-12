# M04 integration request: no shared code modified

The existing consumer contract stays `archive_binding = {root, files}`, where files are exact private archive/evidence SHA256 bindings returned by the unchanged import owner. The original reader returns `records`, `slots`, original payloads/bindings and original record-level errors. Existing manager/current-US integration continues to consume this contract; no field invented for M11/M13/M15/M16/M18 and no formal eligibility inferred.

The new explicit command returns schema `v5.research_ingest_result.v1`, `status`, immutable request/code identity, `archive_binding`, `article_count` and `article_ids`. All natural/PIT/production/trading claims remain false. Original article/body/image/OCR/missing-time fields are transported unchanged, not normalised into a success claim.

P0 may register a read-only material query from this bound reference using its actual API routing contract. No new HTTP URL is claimed live here. Keep original errors, unavailable/missing images and missing times visible; query/refresh/date navigation must never start capture/build/import. Reject stale release identities through P0's existing expected-generation/CAS publication. Publish only after private-root validation and Mac real-data verification; keep prior release for rollback.

Required downstream tests: exact archive reference/cold read, supplied date/cutoff and prior success retained on failure, GET/write-root/job-count invariance, no latest fallback, no implicit conversion of readable material to formal recommendation or relationship. M04 uses no video/M12 or announcement/M13 producer.

Not delivered here: authenticated live provider collection, all-lane orchestration, partial-builder recovery that would violate the original owner guard, actual preview API registration/deployment, natural continuity, or new real-data/PIT facts.
