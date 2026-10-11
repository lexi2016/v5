# Mac draft preparation checks

This is a draft preparation record. It is not a Mac acceptance record or a
final candidate evidence manifest.

- Both helper scripts were parsed with Python's `ast.parse` in the current
  cloud runtime. No packages were installed or changed.
- `mac_generation_walkthrough.py` was smoke-executed against the frozen
  `review_snapshot` in Linux / Python 3.12.14 / pandas 2.2.3 / no pyarrow.
  It completed with exit 0, using only SYNTHETIC rows in a new private directory.
- The final smoke is logged in
  `cloud_check_logs/cloud_draft_walkthrough_smoke_02.json` and its complete
  stdout/stderr companions. UTC start: 2026-10-11T10:55:00.489575+00:00;
  UTC end: 2026-10-11T10:55:02.100983+00:00. The first smoke is retained separately;
  between them only the shared environment description was changed from a
  historical-specific label to `UNCERTIFIED_RUNTIME_DIAGNOSTIC` so the same
  helper correctly describes both engineering and historical-diagnostic runs.
- The smoke proves that the draft helper can execute its two-slot/reuse/new
  configuration/CAS/bad-input/rollback/read-only/HK-sentinel procedure in the
  observed cloud environment. The frozen snapshot still had independently
  reported issues outside that walkthrough's cases; this smoke is not approval
  of that snapshot or the final candidate.
- `mac_real_input_check.py` has not decoded parquet in this cloud environment;
  actual pyarrow is unavailable. Its real-data and Mac execution status remains
  `NOT_RUN`. No fake pyarrow, input normalization, ready receipt, or fabricated
  source timestamp was introduced.
- Both helpers are intended to be copied verbatim into the final package tools
  with an explicit path mapping and SHA in the final package manifest.
  Generated `cloud_walkthrough_smoke*` private roots are preparation artifacts,
  not production inputs and not mandatory final deliverables.

The main draft keeps current Mac Python 3.14.6, pandas 3.0.5 and pyarrow 25.0.1
as observed source facts. It retains the unchanged declared bounds, explains
their incompatibility, and marks actual API/UI/natural/rollback acceptance as
NOT_RUN. The historical 80,017,050-byte source receipt is retained unchanged;
the current 16 MiB JSON admission limit is documented as an additional expected
diagnostic rejection rather than silently worked around.
