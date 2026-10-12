# M11 rollback

No active service was changed. Before integration, reverting the candidate means keeping base 2c408de0888d1e3ab0c3f000d6fc2fa2217bced8 on the integration side; do not force this development branch or rewrite shared history.

After a later authorized integration, disable only that M11 registration and restore its exact verified before-image. `reverse.patch` restores runtime/vendor/test changes in an isolated matching tree; verify with --check before applying. It does not touch shared API/ledger/P0 or V4.

Retain private archived commit envelopes and original successful generations. Do not delete uncertain request markers to force retry. A reader may continue reading exact committed identities; never use latest across date/slot or transform old state into a new natural success.
