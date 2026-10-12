# Existing b2a297 browser static assets

Source commit: b2a2975832aa1cc9f3cc8efc62535c0f07099999.
This is the existing Mac dist from successful npm run build on2026-10-12T10:12:43.071644–10:12:45.241411UTC (exit0), not a rebuild or replacement page.
Original134 frontend source blobs were rechecked against that fixed commit before transfer.
18 unchanged static files,820253 bytes. Every uploaded Git blob matches the local file's calculated Git SHA; manifest.json lists SHA256, Git blob and size per file.

Serve **dist/** as document root:
- /
- /manager-selection/
- /daily-research-command/ is retained original static entry, not newly accepted business functionality.

All referenced original HTML/CSS/JS chunks are retained, including explicit legacy lazy routes. No maps, environment/config files, logs, local binding files, actual response/bundle objects or credentials were included. Text scans found no private absolute-path markers, LOCAL_ONLY/real-bundle-directory markers, private-key/API-key patterns or sourceMappingURL references. These are static application bytes; the source-baked default saved run identifier is intentional application configuration, not a real dataset.

**Cloud browser must use synthetic fixtures only** for same-origin /api/v4/manager/m18/v2 routes. No public deployment, tunnel or remote Mac access is provided or authorized by this transfer. No actual saved business content was uploaded. Do not describe cloud synthetic browser results as Mac real-data page acceptance.

This branch is only an asset delivery. No build/test rerun, UI validation or hosting was performed during transfer. Previous build and real Mac HTTP limitations remain in the integration branch feedback6013cc and7f89dd. The current integration branch and main were not changed.

The assets preserve exact bytes from the recorded output. Their SHA256 values were first inventoried at transfer time; no earlier dist hash manifest is asserted.
