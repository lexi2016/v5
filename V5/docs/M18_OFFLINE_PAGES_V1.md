# M18 offline pages v1: approved slice, synthetic acceptance only

Owner: M18. Base: 74acbd3e6db1350101f6f46d51ab097e57e7271d.
No publisher/CAS, HTTP, frontend, P0, filesystem reader or owner execution.
This format binds an already saved response; it does not establish source/PIT/business admission.

API: build(response_bytes, saved_plan_bytes, expected_identity) -> Bundle(manifest bytes, content-addressed object bytes). Reader(bundle, expected_manifest_sha256, expected_identity) requires caller-held pins, never trusts a self-declared root.

Identity has exactly run_id, target_date, plan_sha256, raw_sha256, response_sha256, input_identity. Build verifies saved raw/semantic SHA and response run/product/readback identity; response must be canonical JSON, excluding parent local_result_transport. No field is deleted or reclassified. Source safety flags must remain research-only; unknown nested fields survive full reassembly.

Generation is deterministic from version, identity and fixed layout. Root manifest commits generation, identity, ordered chunk hashes/offsets/lengths and payload section/item byte spans and hashes. Chunks are bounded base64 envelopes; each includes the identity/generation/sequence. No second copy of large text in detail metadata. Full-response SHA covers exact decoded canonical bytes; saved semantic and raw hashes are separate.

Overview includes content_chunks and lists every payload section with actual total count, loaded_count=0, not_loaded_count=total, state=NOT_LOADED. Empty collections have total=0; absent sections stay absent, not synthetic empty success. Complete top-level fields outside payload remain in full content.

Detail(section, selection, cursor) supports only structural selection {indices: sorted unique nonnegative item ordinals} or null for all. This is NOT symbol/date/business filtering. Array sections enumerate original rows; other fields are one complete value (including null). A fixed 32-entry page returns range/hash/kind references with value_state=NOT_LOADED, matched_total and not_loaded_count. Cursor binds root manifest, generation, full identity, section, selection digest and page offset. Reader validates a received page against its pinned root. Content(index) returns a bounded base64 envelope additionally bound to the root manifest SHA; verify_content compares all fields against the pinned snapshot. Local item_parts yields raw byte slices for reconstructing one indexed value (not standalone transferable records). Large items are read as bounded range parts, with their total length/hash, never embedded wholesale in an overview/detail response.

Limits: strict object/returned JSON response <16 MiB; aggregate manifest+unique stored objects <64 MiB; 10000 stored records and 10000 indexed items; JSON source and objects <=200000 lexical tokens and semantic nodes, depth<=64. Source key bytes <=1024; scalar token length <=128 (strings use bounded scanning). Content block 256 KiB. Raw full reassembly is a local offline operation, not a single HTTP response, and remains subject to total limits. All limits are local to this new owned format; shared budgets unchanged.

Reader rejects wrong root, wrong identity/generation, noncanonical/duplicate-key/unsafe/over-budget input, malformed manifests, missing/extra/reordered/corrupt chunks, bad ranges/counts, cursor/page substitution, cross-section/filter/run/generation, and incomplete reassembly. Parsing and construction are bounded, not a hard real-time deadline. No path, URL, dynamic import or service control is accepted.

Verification: synthetic only, including >16 MiB single text, exact full byte reconstruction, all missing-data flags/gaps, empty/null distinction, ordering, boundary limits and negative identity/page/chunk/schema cases. Existing shared/source/old tests remain byte-identical.


## Required caller request binding

`verify_page(page, *, expected_section, expected_selection, expected_cursor, expected_offset)` requires every expected argument. The caller saves these from the outbound request before receiving the page. `expected_selection=None` explicitly means all indices; `expected_cursor=None` and `expected_offset=0` explicitly mean the first page. Later pages require the saved outgoing cursor and its corresponding integer offset. Offset must be a non-boolean integer and agree with the cursor. The verifier reconstructs the expected page from these caller-held values, not echoed page fields, and compares the complete bounded canonical response. A valid gaps page cannot satisfy a materials request; a later page or different selection cannot satisfy the first-page request.

`verify_content(content, *, expected_index)` likewise requires the caller's requested non-boolean integer chunk index. A valid chunk 1 cannot satisfy a chunk 0 request. Omitting any required expected argument is a Python API TypeError; malformed or mismatched values produce ContractError. There is no legacy self-verification fallback.

Manifest SHA and all run/generation/saved semantic/raw/full-response identities remain bound to the Reader constructed with caller-held `expected_manifest_sha256` and `expected_identity`. Use that same pinned Reader to verify responses for the pending request; do not construct a new Reader or expected arguments from the response under verification. This change does not increase any budget or establish real 30 MB response node/index compatibility; real incremental acceptance remains paused for independent review.
