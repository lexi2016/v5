# Mac fixed M16 loader assembly acceptance

Candidate `5bb1d635abe03cec61d0e52bf1150f2c70b5fe6a` from original M16 branch. The complete fixed tree (171 files) was reconstructed in a new isolated task directory and every Git blob verified, including all 134 source-manifest entries. SOURCE_MANIFEST SHA-256: `c8f72f9a64cb2dd0c1f37819156e7d26ec457097d3f2bffad79f2beeebeac2ea`. All 171 files remained exact after execution. No product edits or dependency installations.

Existing Darwin arm64 Python 3.14.6 / pytest 9.1.1. Only `V5/tests/test_m16_owner_loader.py` ran, with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=V5/src. Exact invocation and environment are in tests.json. UTC 2026-10-13 05:30:46.167551–05:30:48.996992: **32 passed, exit 0**, pytest duration 2.71 seconds. Test network/observation sentinels remained satisfied. 136 protected files and protected listener PIDs were unchanged, including the current M12 real-content preview. No app, job, provider request, collection, credential configuration, V4 write or preview replacement occurred. No broader donor suite ran.

This accepts only manifest-bound loader integrity and the four original objects' offline assembly. Later P0 integration, real observation binding, actual PDF/provider closure, business behavior and full product acceptance remain unverified.

Independent requested M11 environment probe used only two synthetic rows. pandas 3.0.5 with future.infer_string=true converts the None cell to a float nan through DataFrame.to_dict('records'); pd.isna returns true. This supports the fixture conversion hypothesis without modifying pandas configuration or product/fixture source. The 117 M11 tests were not rerun. Raw local diagnostics, private paths and real data are not published.
