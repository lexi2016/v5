# Integration request

No cross-module integration was performed. This module branch is a sparse source overlay, not a complete runnable V5 checkout. `V5/tools/run_m02_isolated.py` verifies and materializes the 72 original handoff files in a disposable directory, then overlays the eight delivered files; it never installs into an active tree.

For later unified integration:
1. Overlay the three complete source files and three tests into an isolated V5 tree containing the exact handoff dependencies. Include the two tools if using the supplied harness.
2. The native reader's only change is `from v5_shadow.m02_input_snapshot import snapshot as _snapshot` in its worker. This removes the manager/announcement business import dependency while retaining the original snapshot boundaries and original owner process/audit/identity logic.
3. Do not replace shared helpers, alter owner manifests/PINs, copy the manager/announcement implementation to satisfy this dependency, or apply rejected R3.
4. Caller persists the returned receiptHash externally and passes that exact anchor to independent readback. No public API/preview/manager consumer has been switched to this wrapper.
5. This source module produces SOURCE_IDENTITY_ONLY records. Original downstream qualification gates remain responsible for eligibility. There is no automatic trading, BUY, production, or historical-PIT enablement.

The two retained original manager end-to-end test references need the complete manager integration tree; they are intentionally not made green through stubs or copied business modules here. Their actual isolated import failures are recorded in TEST_RESULTS.json.
