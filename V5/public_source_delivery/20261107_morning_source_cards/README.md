# Morning Top200 source-card components: public-safe source export

This is code for exact-name text association and a fail-closed result-view
component, not source collection, identity confirmation, a new ranking, or
buy eligibility. It does not implement the complete 07:00–08:00 workflow or
any of the other framework nodes as business jobs.

No original article, source receipt, real stock card, user dataset, SQLite,
private input path/binding, credential, active lock or runtime receipt is included.

## Components

build_cards.py retains its explicit input interface: caller-supplied readonly
SQLite path, three local text records with size/SHA, expected database SHA and
a new output directory. No default private path exists. Missing/mismatched inputs,
wrong Top200 denominator and an existing output directory reject the operation.
Original name-association, date preservation, HTML escaping and UNKNOWN identity/
factual status remain. The concrete historical publication-time warning is
replaced with a general rule: material published after a cutoff cannot be
backfilled as known before the cutoff. A matching digest does not grant source
permission, provenance authenticity or semantic approval.

node_results_api.py has no private date or record bindings; it refuses with
PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING. Original exact-date/source-scope,
size/SHA, bounded local lock and resource callbacks are retained, not broadened.
node-result-view.mjs likewise has no exact record-date binding and its default
loader always refuses without network access. Any future real binding must be
separately reviewed and tested, not supplied as a bypass. UI text continues to
say UNKNOWN, NOT_SENT and historical/manual only. No browser execution verified.

The API/UI cannot render real results from this distribution by design. The
builder may be tested with explicit synthetic inputs; that is not integration
with the production database or a source-admission mechanism.

## Reproduce synthetic checks

Python 3.11+ Linux and existing Node, standard libraries only:

    PYTHONDONTWRITEBYTECODE=1 python -m unittest -v
    PYTHONDONTWRITEBYTECODE=1 PYTHONOPTIMIZE=1 python -m unittest -v
    node --test view.test.mjs

Seven Python tests create an ephemeral SQLite with 200 explicitly synthetic
names and three synthetic text files. They check association without identity
approval, escaped text, changed/missing inputs, exact denominator, no overwrite
and absent API binding. Two Node tests use a minimal fake DOM to test refusal,
not a browser. No original real-result test is copied or claimed here.

## Gates and remaining acceptance

Do not treat these component-level checks as shared production locking or
resource admission. The original authorized orchestrator must enforce its
unchanged shared lock, memory/disk and source gates before integration; this
package is not admitted to that workflow. No task, owner, server, collector,
trade or actual message was started. Keep V4 and original resources intact.

Identity review, factual verification, image review, semantic matching and
buy eligibility remain UNKNOWN / NOT EVALUATED. An unmatched name does not
prove the stock has no relevant theme. Source publication timezone remains as
provided or UNKNOWN, never guessed or backfilled. Browser, live catalog,
production wiring and natural-trigger/business acceptance remain NOT VERIFIED.

PROVENANCE.json records original and changed hashes. Original private candidate
and evidence remain untouched. This export requires independent review before
GitHub submission; upload and remote byte readback are separate later stages.
