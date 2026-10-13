# M06 evening-date correction

Base: f157b59833fc0a10bf04ae9ea5df5d6166be0c64; Mac acceptance feedback 6449bb3348e40fea5edab88dbf8d1df28b10ee49.

1. RED: reproduce scheduled/signal D -> next HK securities session target, including Friday/weekend, half-day/holiday and unavailable next calendar year.
2. Reuse the original frozen calendar states to determine the next session. No calendar-day substitution or inferred half-day midday schedule.
3. Read fixed Mac source/receipt evidence da278dfdc533b83a491762aab9fc96466cf0d0db and the two confirmed JSON-shape clarifications. Adopt the explicitly approved compatibility-adapter path: original M06 bytes unchanged; owner_contract_cutoff is separate from D admission and execution_deadline, never PIT. No invented default cutoff/window end/budget.
4. Once verified, apply the minimal strict scheduled/signal/target distinction to P0 and M06-only dispatcher admission; preserve other lanes, original owner/reader and two-ledger exact identities.
5. Validate readonly source receipt -> exact input inventory -> isolated immutable snapshot -> actual delivery completion. Never borrow panel finished_at as all-input completion.
6. Run only new focused cases and affected small regressions; preserve defaultDisabled. Fresh remote HEAD/changed-files checks and normal CAS; preserve parallel M04 work.

TDD evidence: calendar/date and current-reader failures reproduced; owned-grandchild timeout, cleanup failure, deadline equality, backward-clock expiry, duplicate JSON and input-completion checks each had targeted RED→GREEN evidence. Real original-owner existing-pool synthetic end-to-end mapping, dual ledgers, cold reader, current CAS and one-owner reuse passed. Final scoped regression and source-closure verification recorded separately. No real model/provider run or scheduler enablement.
