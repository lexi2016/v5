# V5 M14 Decimal 80% minimal candidate

Status: candidate only. Not deployed.

Base file SHA256 and candidate SHA256 are in SHA256.txt.

Changed path:
`V5/vendor/rebound_baseline/v4/manager_research/workspace_plan.py`

Change:
- replace the two admission arithmetic comparisons with Decimal comparison at the existing gate location.
- no threshold change: 0.8 and 1.5 unchanged.
- no denominator change.
- no missing values filled.

Not completed:
- AST capsule/pin update
- runtime owner contract update
- formal admission closure
- Mac validation

Test executed:
`python3 -m py_compile workspace_plan.after.py`
