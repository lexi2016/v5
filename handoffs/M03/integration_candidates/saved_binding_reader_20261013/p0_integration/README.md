# Exact-preimage P0 M03-only saved publication candidate

This directory is a candidate, not an applied P0 change. No integration branch was updated. The precise deployed mixed-state preimages were verified by the coordinating Mac task; do not substitute the whole files from an older commit.

Required original bytes:
- V5/src/v5_shadow/source_bundle.py: Git blob 28f63d069c522c213a464a41a0beee9ed61a5455, SHA256 8a1730e25b45cc042abf20ab15f62e33af8f819cad2c9ec1bfc20fb4d4bc2f0e
- V5/src/v5_shadow/source_bundle_worker.py: Git blob 24986aa93eacbdf0c6a4b49660b91c07a1c09ae7, SHA256 782c523c96ce9494c616aac04cb02276e59ced55ff1814309c192e067ec171d7
- V5/contracts/source_owner_runtime.json: Git blob 8b3651ecd61459a1115479d4b97e92bc48d76698, SHA256 4742067f641a56df84d590c5036c4fd27e1cd7fa974519995589e8ecf7f54465
- two new paths must be absent. All exact before/after file identities are in PREIMAGE_AND_AFTER.json.

The patch appends a saved-read branch before the old M03 import, adds one byte-pinned adapter to the existing M03 owner manifest without changing any existing entry, and adds `publish_m03_saved_binding`. It does not change current route inventory, existing M01/M02/M05 behavior, other owner code, request/binding/snapshot bytes, or UI services. Forward apply then exact hashes and reverse apply back to exact original hashes were tested in an isolated directory. Do not reverse a live publication or discard any later changes.

For isolated code staging: check every before SHA/absence, run `git apply --check runtime.patch`, apply once to the authorized isolated/staged P0 tree, and verify every after SHA. Stop on any mismatch. The coordinating Mac task owns actual integration/publication.

Call from the staged P0 runtime's existing Python process after its usual module imports:
`publish_m03_saved_binding(read_request, existing_source_bundle_config, expected_generation=the_current_expected_generation, data_kind='RECORDED_INPUT_REPLAY')`.

`read_request` is exactly `action='read'` plus the four local envelope fields documented in the parent README. The original M03 request retains capture=True and all paths. The saved adapter validates the original efea runtime and reads only; it does not replace the deployed source owner code or need producer access.

Use the original current source_bundle config and current generation from the same existing output root. No config/routes/other bindings are reconstructed. The function pins the exact predecessor record, keeps all other three card rows unchanged, replaces only M03, and uses the original generation CAS publisher. Any reader/hash/config/data-kind/identity/CAS failure occurs before publication and retains the old page. It does not run run_source_bundle, daily_tick, other modules, or any producer. All sibling route record hashes remain intact.

On success, independently read the original /api/v5/source-bundle/status and compare M03 original run/capture/SHA/status/counts plus all non-M03 cards and sibling route hashes. The standalone adapter result is not evidence that the HTTP/page publication already happened. No service restart is requested.

Test: with the actual P0 dependency closure and M03_SAVED_TEST_RUNTIME pointing to an isolated original efea market runtime plus the adapter, run `python -B -m unittest -v test_source_bundle_m03_saved`. The six tests use real original quote-only synthetic data, disk binding and cold reader, actual module generation/CAS storage, and verify other-card/sibling-route retention and failure no-write. `test_support` contains the unchanged synthetic route fixture if it is absent from the consuming test directory; add that directory to test-only PYTHONPATH. No private Mac paths or inputs are in these tests.
