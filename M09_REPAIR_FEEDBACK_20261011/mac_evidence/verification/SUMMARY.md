# M09 fixed candidate Mac independent validation

Candidate d0f9905940584777abbcae248850ebc487cade63. ZIP e39bbd8dad4a603a4412aa01b0d5ffdaeb4259271fdb284c576e9628b03964ad,17258686 bytes,872 members.870 repository SHA/blob identities and759 delivery manifest entries verified.52 before originals unchanged;77 after files equal repository. Forward/reverse patch applied on separate copy with exact whole-tree comparisons. Work remains byte-identical after all tests and probes.

Python3.14.6,pandas2.3.3,pyarrow24.0.0,pytest9.1.1. Reused existing isolated supported interpreter/dependencies without installs/global edits. Process TMPDIR is new non-symlink workspace directory. Every command/cwd/environment/version/stdout/stderr/exit/elapsed saved.

Original fixed suite125/125 PASS,zero skips,33.716s. All4 pyarrow cases executed. Independent original review6/6 PASS,3.763s. Pyarrow emitted sandbox CPU-cache sysctl warnings; raw stderr retained and decoder tests passed. Generation walkthrough passed,1.988s,private synthetic fixtures only.

Real historical10/09 panel decoded without changes:5126 rows/unique members,2 missing bar_close_pos,137 empty name,240 empty industry code and name. Two historical slot admission/attempt rejection paths confirmed; no served successful generation. Original and copied bytes unchanged. Real decoder diagnostic2.611s. Helper diagnostic_result.json hardcodes acceptance_class=UNCERTIFIED_RUNTIME_DIAGNOSTIC even though recorded actual versions meet contract; this label was not edited and does not imply natural/data admission success.

BLOCKING independent negative: run_a_close_daily a_close_daily.py738-742 returns an existing receipt after checking only request_sha256. Six private SYNTHETIC probes each first create a real FAILED attempt (SOURCE_SHA_MISMATCH). Keeping request_sha256, alter one of schema,date,trigger,safety(orders_sent=true),status(SUCCEEDED with invented run/generation),or remove required fields. Every same-request retry returns the corrupted receipt unchanged; no rejection. Probe exit1 intentionally denotes failure of required rejection. No producer success, head, actual order, external effect or live data involved. This confirms duplicate-return validation bypass, not a demonstrated bypass of independent public generation reader.

Original M09 should validate persisted receipt schema,exact target/slot/trigger/request identity,safety,status-specific required bindings and trusted commit/readback before idempotent return; malformed receipt must fail closed and preserve valid prior output. Add these regression negatives; no local business patch or weakened tests supplied.

Shared ordinary API/UI/dispatcher integration remains three requests only.125+6 passing does not cover this new negative or complete deployment. No browser,8873/8910/61796 service,V4 roots,market fetch,trades or natural slots touched. Future10/12 inputs not used. Candidate remains blocked pending original M09 repair and shared integration review.
