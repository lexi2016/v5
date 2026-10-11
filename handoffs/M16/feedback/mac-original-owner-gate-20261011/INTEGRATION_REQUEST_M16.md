# M16 integration candidate

## Added

- `V5/src/v5_shadow/manager_factory.py`
  - isolates runtime root and owner service binding
  - fails closed without approved bindings
- `V5/src/v5_shadow/manager_loader.py`
  - declares source-closure boundary

## Deliberately not changed

- shared router
- gateway
- M18 workspace owner
- module_api read-only reader
- frozen loader manifest

## Required integrator work

1. Bind the original ManagerResearchJobService with the original Store, ObservationReader and ResearchSourceProvider closure.
2. Mount either the original manager research router or a reviewed narrow job route composition.
3. Preserve existing same-origin/date/body validation.
4. Keep missing real provider activity as fail-closed.

Current status:
- code candidate: READY
- production source activity binding: NOT_RUN
- HTTP integration: NOT_RUN
- Mac acceptance: NOT_RUN
