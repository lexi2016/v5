# M12 ae8239 Mac targeted retest — 4 PASS ONLY

Fixed candidate: `ae8239c7f35651d3d18438ee3febb58c4d60d519`.
Reader blob: `70e7a720312efcbababf3e69e67dd2c821c8428a`.
Original branch: `dev/m12-github-handoff-20261011`.
Previous failure feedback: `444ca97c90ed63862ba72ebaf61181acc5bac30b`.

Reused existing M12 Python 3.14.6 / pytest 9.1.1. Ran the same four supplied synthetic lifecycle tests once in a new task-isolated directory. All 11 source/vendor/test blobs matched the fixed tree before and after; no product edits.

Actual command from fixed candidate root:

```text
<EXISTING_M12_PYTHON> -m pytest tests/m12/test_video_fupan_default_chain.py -vv -p no:cacheprovider --basetemp=<EVIDENCE>/tmp/pytest --junitxml=<EVIDENCE>/junit.xml
```

Start UTC: 2026-10-12T07:15:58.757969+00:00.
End UTC: 2026-10-12T07:15:59.067167+00:00.
Actual pytest exit **0**; **4 passed in 0.22s**.

- PASS same input reuses committed run without new simulated capture/ASR.
- PASS failed publish keeps previous success and readable old run.
- PASS existing valid run with symlink artifact is rejected (previous failing case).
- PASS path escape with valid receipt is rejected.

Full sanitized stdout is adjacent; raw logs/JUnit retained locally. No real acquisition, real ASR, trading, deployment, browser, P0 retest, or expanded audit. This is four targeted synthetic tests only, **not full M12 acceptance**. Natural execution and broader integration remain NOT_RUN.
