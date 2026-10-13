# Mac c5ba navigation preview verification

Fixed navigation candidate: c5ba22fa622d6a1797e20a4fa33997978e7b39b1 (parent af758f0beeb3e9518de05e62a0af23f9e032690c).
Composition: frontend base 287de959 + HkPreselectionPool 0332c6b + four fixed c5ba files. Backend remains 287de959. No local product edits.

PASS: Node 3, Vue 9 (new navigation 7 + existing view 2), build; commands/start/end/exit in checks.json. Checks ran 2026-10-13 10:47:37–10:47:39 Asia/Shanghai.
PASS: front-only 54780 switch 10:52:23–10:52:26 Asia/Shanghai. Verified old owned Vite PID 55214 command/cwd/index before stopping. New PID 59386. Source 65413/PID55204 and manager 63668/PID17107 retained; no backend restart or binding change. All 19 served dist bytes match manifest. Protected listeners and 174 file hash/size/mtime records unchanged.
PASS: full built main bundle mounted via jsdom and real local read-only HTTP, exit 0. Same M18 run 46596b03c2ab4e29b1219fd2e5eb698f. Result area precedes sources; sources closed initially. Announcements32, rebound31, US3, manager1 table row. Navigation focuses result heading; scrollIntoView invocation observed (not physical scroll coordinates). Loading/error inside result before sources; invalid run validation clears old result; restoring original run reads32 announcement cards. Source navigation expands details and focuses summary. M06/M17 each100 rows remain. No JS errors. Error case uses invalid run input and local validation, not a fabricated backend outage.
PASS: M06 full committed reference and all100 saved artifact rows exact; M17 semantics and M18 descriptor exact. No model recomputation, collection, trading, daily scheduling, binding update, credentials or protected system configuration access.
NOT REACHED: browser visual/viewport validation because IAB previously reported Browser is not available: iab; not retried. DOM order/focus assertions do not establish pixel positions.

Library static dist ZIP: libfile_49d31bb752908191b9c7311a6282f192. SHA256 30841b505f548608588068e14ceffc0f616167c99b162fa56c439636b9ea93fc, 270682 bytes, 19 entries (zip.json). Contains frontend static build only.

This verifies the scoped navigation preview; it does not accept all 18 modules or P0–P5. Existing business PARTIAL/CANNOT_CONFIRM and source gaps remain.
