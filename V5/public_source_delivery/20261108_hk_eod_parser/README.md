# Offline HK EOD parser candidate: public source only

Source adapter is unchanged. Tests are newly generated synthetic bytes, fictional future date, artificial prices and test scope. No real three-stock sample, response, official list, request receipt, credentials or binding is included. No unified-controller files are included; that separately blocked export remains pending confirmation.

Run `python -B -m unittest test_public` or `python -B -O -m unittest test_public`: six offline tests. URLs are synthetic provenance strings validated offline, never fetched. This package does not collect, write a production database or activate a provider.

pre_close stays UNKNOWN and is never inferred from preKPrice. Futu price/unit/scope equivalence, CAS evidence and full eligible scope remain UNKNOWN. Structural scope assertions alone do not certify real authority. The original 600-row/full-coverage requirements are not bypassed. production_allowed and original_contract_export_allowed remain False. Parsing is not source admission, production integration or natural/business acceptance; runtime independent_review remains conservatively PENDING.
