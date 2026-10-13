# M12 selected native saved-run migration contract

Selected real native run: 20261012 / BV1eKpR6TEAN / rcv1-20261012-BV1eKpR6TEAN-a802b45429651e71. This handoff contains only observed JSON key/type structure, necessary identity/status values, and 15 artifact roles/relative paths/byte counts/SHA256 values. It is NOT a source manifest or replacement owner receipt. Original metadata bytes remain private and must be preserved on Mac; do not recreate them from this redacted structural description. Array shapes are observed variants, not a complete normative schema.

The existing native manifest is VideoEvidenceV1 (21974 bytes); owner receipt is ReviewCoreReceiptV1 (2007 bytes), ACQUIRED and bound to the manifest raw-byte SHA. All 15 original artifact SHA values were verified by the preceding read-only inventory (46704778 bytes total). artifact_refs uses native field `size`; the contract also supplies measured `bytes`, verified equal. `source_path` and configuration/tool path values, discovery URLs/errors, uploader/account fields, media and ASR text are omitted. Their key/type structure remains visible only where needed to preserve original metadata as opaque bytes. Never rewrite private-path fields inside source bytes just to manufacture a new hash.

Preserve ASR_REVIEW_REQUIRED, transcript_reviewed=false, stockdict_status=NOT_AVAILABLE, VIDEO_GAP_AUDIT_EMPTY and all research-only safety boundaries. This material does not prove completed human review, natural daily acceptance or a new owner execution. No missing owner receipt must be constructed: this selected run already has the exact native owner receipt; its digest is included.

## Fixed existing interfaces (no duplicate source package)

All links below use product c353334d70972033ae86f7175504ca675bafbb68:

- [Original reader](https://github.com/lexi2016/v5/blob/c353334d70972033ae86f7175504ca675bafbb68/V5/src/v5_shadow/video_fupan_reader.py): read_committed_video(root, trade_date, run_id); _read_owner_evidence checks canonical review/DATE/runs/RUN/{manifest,receipt}.json, exact owner identity, receipt manifest_sha256 and original artifacts. Original reader Git blob 2726b1561e31c71fbca54ab50fe95c70d9521071, unchanged from 4bbf069b435d8f0ba28db8e2eba1d358ea5e283c.
- [Saved projection](https://github.com/lexi2016/v5/blob/c353334d70972033ae86f7175504ca675bafbb68/V5/src/v5_shadow/m12_readonly_worker.py): project(binding), exact .v5-m12-root marker, pinned wrapper manifest and native owner receipt; artifact count<=256, each<=256MiB, total<=512MiB; original reader first, transcript/segment each exactly one, display capped at262144 characters. No latest selector.
- [Binding/API adapter](https://github.com/lexi2016/v5/blob/c353334d70972033ae86f7175504ca675bafbb68/V5/src/v5_shadow/m12_readonly.py): validate_reference, validate_binding, verify_runtime, read_record. Exact binding keys: private_root, trade_date, run_id, manifest_sha256, owner_receipt_sha256, data_kind, python_executable.
- [Existing wrapper layout](https://github.com/lexi2016/v5/blob/c353334d70972033ae86f7175504ca675bafbb68/V5/src/v5_shadow/video_fupan_daily.py): envelope construction and immutable wrapper pair inside run_video_fupan. Format reference only: that function invokes the producer and must NOT be called to import this historical saved run.
- [Runtime source pin](https://github.com/lexi2016/v5/blob/c353334d70972033ae86f7175504ca675bafbb68/V5/contracts/m12_runtime.json).

## Missing integration, not missing native evidence

The original store has no V5 root marker and no video_fupan/runs/DATE/RUN wrapper manifest/receipt. A legitimate import candidate must explicitly record historical migration, preserve native manifest/receipt and all root-relative artifact bytes in an isolated V5 root, validate before publication, and avoid producer/provider/download/ASR. Do not fabricate a wrapper as if the original owner ran again, mutate original current pointers, or mark ASR/stock dictionary complete. No import, copying of original data, configuration binding, test, build or deployment was performed in this handoff task. Mac will independently apply an approved import candidate later.
