# HK observation timestamp preservation

Baseline: fc9ea68a2432dcfb279745d65819d3d853f5321a.

The existing HK09 availability gate was correct after parsing, but Python's
`datetime.fromisoformat` silently discarded fractional digits beyond six.
Consequently an input available 100 nanoseconds after 09:00 could be accepted
as exactly 09:00. The parser also discards a fractional offset when its whole
hours/minutes/seconds are all zero. Both cases can alter the stated instant.

`capture.stamp` now rejects fractions finer than microseconds before parsing.
For signed offsets it compares the explicitly declared offset duration with
the parsed `utcoffset`; a non-preserved offset is rejected. Representable UTC,
minute offsets, second offsets and up to six fractional digits remain usable.
Existing HK09/continuous-close/CAS date, ordering, source, scope, calendar,
owner, lock and admission rules are unchanged.

`bridge.dispatch` consumes `capture.py` through a fixed `CAPTURE_SHA` and
executes the exact bounded bytes that were checked. An ambient module named
`capture` cannot substitute different implementation bytes. Empty registrations
still block before dependency loading. This is a repository consumer binding,
not scheduler registration, provider admission or production activation.

Input and output schemas are unchanged. Unsupported evidence raises ValueError
before time-boundary comparison. A registered bridge maps such errors to its
existing BLOCKED result; no gate is lowered and no source/owner identity is
created. The original formula and M10 reader are not changed.

From this directory, run:

    python3 -B -m unittest discover -v
    python3 -O -B -m unittest discover -v

The new regression tests exercise pure timestamp/validate functions and public
empty-registration or dependency-refusal paths. They call no collector and
perform no source requests or delivery. `BASELINE_RED_normal.txt` and
`BASELINE_RED_optimized.txt` record failures against the original bytes;
`TESTS_normal.txt` and `TESTS_optimized.txt` record the fixed candidate.
Existing collector-path tests are outside this no-collector verification.

Before integration, the integrator must refresh the package MANIFEST entries
for capture/bridge and the new test/document; update their PROVENANCE as derived
from the baseline rather than claiming unchanged original bytes; and refresh
the repository-wide publication manifest. Any external controlled adapter
registry must separately rebind both new code pins under its original review.
No historical REGISTRY is rewritten by this patch.
