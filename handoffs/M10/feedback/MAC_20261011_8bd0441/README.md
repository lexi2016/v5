# M10 Mac isolated acceptance — FAIL

Tested fixed candidate: `lexi2016/v5@8bd0441b1c6d7847d532adb5af28a3e49221db98`.
Product source: `V5/src/v5_shadow/hk_close_daily.py`, Git blob `85e64fb2742de4c8b3597f14e4acc795ea87ec43`, SHA-256 `7afcacd41f481ed65a505e287602c3c117d511b0d260dd7a14109856c0c7714e`, 3907 bytes.
All five fetched source/document files matched Git blob IDs; detailed SHA-256 and byte counts in source-manifest.json. This was a minimal fixed-file extraction, not a complete repository checkout.

## Results

- PASS: original targeted tests 2/2, pytest exit 0.
- FAIL: independent publication integrity probes 2/2 failed, pytest exit 1. After publishing a synthetic review with a publication digest, removing publication.json or replacing its generation still returns the review. Expected: reject missing/mismatched publication before returning payload. Actual: no exception. Reader only checks payload digest and manifest digest; it never reads publication.json.
- PASS: two independent read-side checks: files' bytes/size/mtime unchanged on successful read; absent root stays absent after failed read. This is bounded filesystem evidence, not an OS-wide syscall audit.
- NOT_RUN: real/default frozen-owner producer chain, original frozen canonical integration suite, network collection, current-day market run, API/UI, deployment, safety/CAS/failure-preservation verification. No claim that existing deficiencies are repaired. `_load_frozen_owners` remains ordinary ops imports without fixed-source provenance validation. Existing two tests do not exercise it. No synthetic owner substitution was presented as a successful default chain.

## Reproduce

Run `python3 run_acceptance.py` with the recorded isolated dependency environment and fixed source extraction. Exact argv and process-only environment are in commands-final.json. Python 3.14.6; pytest 9.1.1. Synthetic data only, local private TMPDIR. `test_independent.py` is the minimal failing repro. Raw original and independent logs are included.

Initial collection exit 2 was an acceptance harness issue: reused dependencies have a .pth entry exposing a different product checkout; namespace import did not find this candidate. Retried with Python -S and an explicit site-packages path, which suppresses .pth processing. Initial commands/logs are retained. No candidate source modifications or global environment edits were made. Referenced root V5/docs/M10_HK_CLOSE_HANDOFF.md and root v5_shadow/__init__.py both returned GitHub 404 at this fixed commit; neither was fabricated.

Only this separate feedback directory is proposed for GitHub commit. No product edits, merge to main, browser access, services/ports 8873/8910/61796, trading, credentials, or security settings were touched. These findings require correction in the original M10 development workflow before integration approval.
