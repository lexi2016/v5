# V5 Candidate and Historical Source Index

Snapshot baseline: `01d93717905813705732161d4d79062ae5af2d99`.
This index classifies known candidate refs from the fixed handoff source index. It is deliberately conservative: "candidate" means reviewable source, not accepted integration.

## Status definitions

- `PARTIALLY_INTEGRATED`: selected parts are present in the integration snapshot, but the source branch is not fully integrated/accepted.
- `PROPOSED`: candidate is available for scoped review; inclusion not established.
- `REJECTED_OR_SUPERSEDED_PARTS_PRESENT`: source tree includes rejected/before/after alternatives; use the exact manifest, not a whole-tree overlay.
- `BOUNDED_EVIDENCE_ONLY`: some test/runtime receipts exist for the stated scope; full module acceptance is not established.
- `UNKNOWN`: current branch head or source relation has not been freshly checked.

## Known module candidate refs

| Module | Candidate commit | Snapshot classification | Required handling |
|---|---|---|---|
| M01 | `ea96a80cf9d79e638ee08e15cb0bf92368261ada` | PROPOSED | Read owner manifest; preserve formulas, PIT and source generation |
| M02 | `776acce9328aa102e3db6973405f01260f15239d` | BOUNDED_EVIDENCE_ONLY | Preserve successful capture/readback evidence; qualification/PIT remains unconfirmed |
| M03 | `3020bb6b0abd30fc9a243cfdee7ec0f121e2c178` | BOUNDED_EVIDENCE_ONLY | Use real-session receipts for the bounded successful path; no natural full-chain claim |
| M04 | `0bb46df890d4b1a57fcc17982a9800cac2f18146` | BOUNDED_EVIDENCE_ONLY | Preserve source acquisition, recovery and publication-rejection receipts |
| M05 | `5d868fc09fba7f7fe210e603a28015e271117077` | PARTIALLY_INTEGRATED | Integrate only manifest-selected owner changes; preserve v192 valid-empty adapter |
| M06 | `ddb07572e7bd24efff2a9624806e2487129d208a` | BOUNDED_EVIDENCE_ONLY | Distinguish bounded natural step from complete natural chain |
| M07 | `e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31` | PROPOSED | Verify source owner closure and full target window before integration |
| M08 | `01f1a6347722081cbbf97b54204bf033e6d01938` | PROPOSED | Verify all original stages including Stage 8 and real inputs |
| M09 | `3d1d04283f4d5ca05923b05c496a97e79145d275` | REJECTED_OR_SUPERSEDED_PARTS_PRESENT | Keep before/after/history separated; do not overlay entire tree |
| M10 | `9ab214b0ad5542111c04d10f50cac989644205f7` | PROPOSED | Preserve original close logic; verify scheduler and new-day execution separately |
| M11 | `6abba1b36dce3d9696b5a0e401ba86a96d9b10ec` | PROPOSED | Verify six-slot source/identity closure; retain genuine WAITING |
| M12 | `385b1068054f3d20688344961b3a3cf34d6a7bb4` | PROPOSED | Preserve lifecycle/retry and ASR_REVIEW_REQUIRED semantics |
| M13 | `308af26862daf005c5c5800d15c5053c84275938` | PARTIALLY_INTEGRATED | This is only a 10-file partial-pages supplement, not the full announcement owner branch |
| M14 | `ad9a61d26c487748ba017b69250571ae5a38bbab` | BOUNDED_EVIDENCE_ONLY | Preserve pending/unknown states; do not infer qualification from page visibility |
| M15 | `821a25b1667a28073360c96cf8702ab57dbd233f` | BOUNDED_EVIDENCE_ONLY | Keep seed and material paths separate; verify dependency lock and real eligibility |
| M16 | `d18469212c86bec95303ca746cb4b90dd9a863de` | BOUNDED_EVIDENCE_ONLY | Cache-root limited evidence is not full lifecycle acceptance |
| M17 | `6d459cbc1e694eed413d142c75be64241a727e7f` | BOUNDED_EVIDENCE_ONLY | Preserve fixed owner closure; synthetic cold import is not the real 15:30 window |
| M18 | `5c327e45d99468d0ade73ee4acff6e0130f02852` | BOUNDED_EVIDENCE_ONLY | Use exact saved manager product references; three-lane same-run closure remains open |

## Additional known supplements

| Candidate | Commit | Classification | Rule |
|---|---|---|---|
| M14 stored supplement | `a20ea3b04cac63fbbfc4610e891ae1f6e8c171ba` | PROPOSED | 10-file supplement; do not replace M14 source tree wholesale |
| M18 daily assembly | `eae78ea4d2842a71d64721ae0f633e5583e80642` | PROPOSED | 4-file supplement; validate against fixed integration owner |
| M18 offline pages | `325730f0979a9989d53dd0ff3bade5b238912455` | PROPOSED | 4-file supplement; preserve source and publication contracts |
| M18 offline v2 | `8bea98c2bd506d42c00f2616dd04949d7a2b232d` | BOUNDED_EVIDENCE_ONLY | 17-file supplement; offline success does not prove live deployment |
| M09 candidate r1 | `d0f9905940584777abbcae248850ebc487cade63` | REJECTED_OR_SUPERSEDED_PARTS_PRESENT | 870-file tree with before/after alternatives; never whole-tree overlay |

## Required candidate review receipt

Every newly reviewed candidate must add a receipt containing:

1. Candidate branch and full HEAD SHA, plus integration base SHA read immediately before work.
2. Source owner manifest/PIN and exact selected file list with old/new blob SHA.
3. Dependency/config lock changes, if any.
4. Tests run with exact command, environment, exit code and log hash; all NOT_RUN/skipped tests listed.
5. Failure/recovery and immutable cold-read evidence.
6. API/page/browser evidence, clearly distinguishing HTTP/DOM from native visual inspection.
7. Real input and natural-run receipts, or explicit NOT_RUN.
8. Integration disposition and rollback path.

No branch should be marked integrated solely because it exists, shares some Git blobs, or has historical test receipts.
