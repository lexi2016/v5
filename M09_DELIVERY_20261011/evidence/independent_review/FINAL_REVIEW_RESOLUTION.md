# M09 targeted independent review — resolved

**Review status: APPROVED for closure of IR-01, IR-02, IR-03 and IR-04 on the
exact source identities below.** No outstanding blocker remains from this
independent review. This is engineering review approval, not Mac, real-data,
live API/UI, natural-slot, or complete-business acceptance.

The initial findings and RED reproductions remain preserved in
`REVIEW_FINDINGS.md` and the original logs. The first executing-code fix also
received a targeted residual check for pre-imported shared helpers; its RED
is retained in `independent_preimported_helper_red.*`.

## Exact reviewed source

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `V5/src/v5_shadow/a_close_daily.py` | 55584 | `23b4200ffb29e83041b761927c6f285ff84d6b92a3cf8b2fc3e527a9d8ae1d9c` |
| `V5/src/v5_shadow/a_close_daily_worker.py` | 2489 | `29eaf1e3a912d7bd09c0150dc3a260e371f982479a6afaf42f9b86a84a109611` |
| `V5/src/v5_shadow/a_close_daily_sources.py` | 18587 | `b9c690059324d208c9fe510075efd2f3447135bc1e29f9b6f9be39afb41829b6` |
| `V5/src/v5_shadow/a_close_daily_api.py` | 17977 | `74c4925c4ba5aa0d973ead806fed57cdf3416db08db0c1124b2e5fcf84003c16` |
| `V5/src/v5_shadow/contracts.py` | 7256 | `eee026873e0d765fcedf52077daea823edf6ee7013f37c106c82b66a4582d85a` |
| `V5/src/v5_shadow/digests.py` | 425 | `134b1a13b7ff677afef6f556e2a750d94cc54a396cbdcff111c5d67e645280e5` |
| `V5/contracts/m09_a_close_daily_source_manifest.json` | 13432 | `7e4f5eb41e0c8f6fc062d9d3f130af47a39eb5ae82a19389c9a5c0788a04901d` |

Root reviewed: `/workspace/scratch/a5458cb06b78/m09_work/after`. The final
candidate commit is assigned by the coordinator; this review does not invent
a repository publication identity. Shared contracts/digests remained unchanged.

## Resolution assessment

- **IR-01 closed.** Generation identity binds the creator trigger and request.
  Public reads require the matching successful immutable trigger receipt.
  An incomplete head is not served; the reader may expose its verified same-day
  predecessor with separate recovery metadata. Explicit uncommitted generation
  reads fail, and the next date-locked mutation reconciles the interrupted head.
  The original real-child `os._exit(73)` reproduction now serves the old
  generation both before and after retry. Retry remains honestly UNKNOWN.
- **IR-02 closed.** `_read_run` verifies calculation raw/canonical hashes,
  record identities, the exact retained-input set and metadata, every input's
  size/digest, saved manifest/source/panel/member/receipt relationships, and
  the original producer pointer. Historical absolute pointer bytes remain
  bound to their recorded creation root without dereferencing that old root.
  Each of the four original corruption cases now yields CANNOT_CONFIRM.
- **IR-03 closed, including the residual cache path.** Daily pins/checks its
  implementation files, requires the unchanged shared helper source baseline,
  compares imported bindings and executing helper code objects with code
  compiled from verified bytes, checks the digest size constant, and passes an
  implementation identity to the independently checking worker. A changed
  loaded daily file, a helper imported before its disk file changes, and a
  changed helper cached before the original file is restored all fail closed.
  Shared modules are neither reloaded nor edited.
- **IR-04 closed.** The pure API projector requires the exact three date-bound
  store metadata entries and links the advertised raw-review SHA to the entry
  in the hashed record. The original arbitrary-zero digest reproduction now
  returns CANNOT_CONFIRM and no fabricated raw digest.

## Final independent execution

`independent_final_all_green.json` records the actual command, working
directory, selected candidate environment, UTC/Shanghai start/end, exit, and
complete log hashes. Actual UTC interval: 2026-10-11T10:58:33.798850+00:00 through
2026-10-11T10:58:39.227034+00:00. Result: **6 tests run, all passed, no skips**.
The input-corruption test contains four separate subcases.

```text
python -B -m unittest -v test_review_findings test_api_raw_digest \
    test_preimported_helper_identity test_restored_helper_identity
```

Environment selected:

```text
M09_REVIEW_SNAPSHOT=/workspace/scratch/a5458cb06b78/m09_work/after
PYTHONPATH=/workspace/scratch/a5458cb06b78/m09_work/evidence/independent_review
cwd=/workspace/scratch/a5458cb06b78/m09_work/after
```

Full stdout SHA: `9e7f7a7ea27d5ad94d72f0fbe248775b60a7417b49120fda56d1518ac0bed338`.
Full stderr SHA: `94a0e8649c21d852ee41e56ca8bf0b3ee3e08a765fb506189ccc807805fd7573`.
The added reverse-cache test explicitly requires
`M09_CACHED_SHARED_HELPER_MISMATCH_RESTART_REQUIRED`, proving that the code-object
comparison path ran even though the restored on-disk helper SHA matched the
original baseline.

All fixtures are SYNTHETIC and all destructive test mutations stay within
temporary copied candidates/private roots. Neither `after` nor the original
review snapshot was edited by this reviewer. No dependencies were installed.
Real parquet decoding and all Mac/live/natural claims retain their actual
NOT_RUN/BLOCKED status. The separate Mac acceptance draft and helper preparation
checks are described in `evidence/mac_draft/DRAFT_VALIDATION.md`.
