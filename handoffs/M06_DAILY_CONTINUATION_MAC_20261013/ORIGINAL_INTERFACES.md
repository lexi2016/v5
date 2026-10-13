# Original interface excerpts (read-only evidence; not executable V5 implementation)

These minimal existing source excerpts preserve the observed interfaces. Relative paths are within the named logical source family. Full-file SHA256 identifies the observed file; no claim that these local revisions are identical to another GitHub version. Source files and private receipts/data are not uploaded.

`ACTIVE_SCHEDULER_APP` is the installed scheduler application selected by its LaunchAgent. `PANEL_UPDATER_PACKAGE` is the separately pinned updater package selected by that configuration. Do not resolve either from the old `current` symlink.

## ACTIVE_SCHEDULER_APP/ops/run_scheduled_slot.py

Full-file SHA256: `c9ce4a348c9232e2690457c9b54c4d9d393b27c4ddac04d318fb6a2e93636b2b`.

Original lines 57–58:

```python
PRESELECTION_SLOTS = frozenset({"1730", "1800"})
NEXT_TARGET_SLOTS = frozenset({"1730", "1800", "2001", "2115", "2140"})
```

Original lines 103–112:

```python
def compute_dates(*, business_date: str, slot: str, calendar: MarketCalendar | None = None) -> dict[str, str]:
    if slot not in ALL_SLOTS:
        raise ValueError("UNKNOWN_SLOT")
    business_date = _date8(business_date, name="BUSINESS_DATE")
    calendar = calendar or load_market_calendar()
    states = resolve_market_states(calendar, business_date)
    if all(state is TradingDayState.UNKNOWN for state in states.values()):
        raise ValueError("CALENDAR_UNKNOWN")
    target = next_trade_day(business_date, calendar=calendar) if slot in NEXT_TARGET_SLOTS else business_date
    return {"scheduled_date": business_date, "business_date": business_date, "target_date": target}
```

Original lines 115–124:

```python
def run_scheduled_slot(
    *,
    data_root: Path,
    slot: str,
    business_date: str,
    scheduled_date: str,
    target_date: str,
    ledger_root: Path,
    timeout_seconds: float = 600.0,
    a_daily_timeout_seconds: float | None = None,
```

## ACTIVE_SCHEDULER_APP/domains/runtime_policy.py

Full-file SHA256: `0575df80b82b7940505fd4509a09e6ac6588245cc1141143b11ac42b4b84a6d2`.

Original lines 65–86:

```python
    market: dict,
    state: TradingDayState,
    slot: str,
    requirement: SessionRequirement,
) -> bool:
    if state in {TradingDayState.NON_TRADING_DAY, TradingDayState.UNKNOWN}:
        return False
    if requirement is SessionRequirement.DAY_ELIGIBILITY_ONLY:
        return True
    if requirement is SessionRequirement.SESSION_OPEN:
        sessions = (
            market["half_day_sessions"]
            if state is TradingDayState.HALF_TRADING_DAY_AM
            else market["full_day_sessions"]
        )
        return any(session["start"] <= slot < session["end"] for session in sessions)
    close = (
        market["half_day_close"]
        if state is TradingDayState.HALF_TRADING_DAY_AM
        else market["full_day_close"]
    )
    return close is not None and slot >= close
```

## ACTIVE_SCHEDULER_APP/infrastructure/scheduling/executor_registry_preselection.py

Full-file SHA256: `cbf533005dd3dc0e7c09f001c7efff0570e979aeee73f179d8b4f79a319c9a39`.

Original lines 263–291:

```python
            update_result = self._run(
                "scripts.update_hk_0_2_panel",
                [
                    "--asset-root", str(self.shared_data_root / "assets" / "hk_0_2"),
                    "--tdx-root", str(self.hk_0_2_tdx_root),
                    "--through-date", request.business_date,
                ],
                cwd=self.shared_package_root,
                env=trusted_env,
                python_executable=self.hk_0_2_python_executable,
            )
            if update_result["status"] != "SUCCEEDED":
                update_result = dict(update_result)
                update_result["lane"] = "HK_CONNECT"
                update_result["status"] = "CANNOT_CONFIRM"
                hk_lane_degradations.append(update_result)
        security_result = self._run(
            "ops.ensure_hk_security_master",
            [
                "--store-root", str(self.shared_data_root),
                "--universe-root", str(self.hk_universe_root),
                "--shared-package-root", str(self.shared_package_root),
                "--trade-date", request.business_date,
                "--futu-python", str(self.shared_futu_python_executable),
                "--prepare-exact-date",
            ],
            cwd=self.repo_root,
            env=trusted_env,
        )
```

Original lines 301–322:

```python
        elif update_result["status"] != "SUCCEEDED" or security_result["status"] != "SUCCEEDED":
            # Preparation may run when its own output is absent. Scoring must
            # wait until both original-owner prerequisites have succeeded.
            failed_input = update_result if update_result["status"] != "SUCCEEDED" else security_result
            hk_result = dict(failed_input)
            hk_result["modules"] = ["scripts.materialize_hk_0_2"]
            hk_result["producer_called"] = False
            hk_result["first_gate"] = (
                "HK_PRICE_PANEL" if update_result["status"] != "SUCCEEDED" else "HK_SECURITY_MASTER"
            )
        else:
            hk_result = self._run(
                "scripts.materialize_hk_0_2",
                [
                    "--store-root", str(self.shared_data_root),
                    "--asset-root", str(self.shared_data_root / "assets" / "hk_0_2"),
                    "--signal-date", request.business_date,
                    "--target-date", request.target_date,
                ],
                cwd=self.shared_package_root,
                env=trusted_env,
                python_executable=self.hk_0_2_python_executable,
```

## ACTIVE_SCHEDULER_APP/infrastructure/scheduling/dispatcher.py

Full-file SHA256: `d186949486f1807c72f4795ff273f1ee886afb536a82e8a328b13bc4cb9f1bf3`.

Original lines 403–406:

```python
    if ledger is not None:
        payload = receipt.to_dict()
        payload["finished_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        ledger.write_receipt(receipt_path, payload)
```

## ACTIVE_SCHEDULER_APP/ops/macos_research_panel_daily_gate.py

Full-file SHA256: `fc852dcbbcde3e3a6bfcf9ea6af46ea773cefe32e00355594edc1a4816665b34`.

Original lines 357–367:

```python
def _receipt(root: Path, lane: str, target_date: str, outcome: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        **dict(outcome),
        "schema_version": "v3.macos.research_panel_receipt.v1",
        "lane": lane,
        "target_date": _date(target_date),
        **SAFETY_FLAGS,
    }
    root.mkdir(parents=True, exist_ok=True)
    _atomic_write(root / f"{lane.lower()}-{_date(target_date)}.json", (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    return payload
```

## ACTIVE_SCHEDULER_APP/ops/macos_research_panel_daily_authority.py

Full-file SHA256: `6b709403414d362bca0bf997a2be55cc7c833361b4a9c465cbf1f7a129827303`.

Original lines 1040–1043:

```python
def run_hk_0_2_authority(updater_script: Path | str, python_executable: Path | str, asset_root: Path | str, tdx_root: Path | str, target_date: str) -> dict[str, Any]:
    target = _date(target_date)
    argv = [str(python_executable), str(Path(updater_script)), "--asset-root", str(Path(asset_root)), "--tdx-root", str(Path(tdx_root)), "--through-date", target]
    completed = subprocess.run(argv, shell=False, check=True, capture_output=True, text=True)
```

Original lines 1095–1099:

```python
    if not isinstance(outcome, Mapping):
        raise SnapshotGateError("HK authority output is not a JSON object")
    if outcome.get("status") != "READY" or _date(outcome.get("through_date")) != target:
        raise SnapshotGateError(f"HK authority through-date postcondition failed: {outcome}")
    return {**outcome, "target_date": target, "argv": argv, **SAFETY_FLAGS}
```

## PANEL_UPDATER_PACKAGE/shared_data/hk_0_2.py

Full-file SHA256: `45a5091cb26800b7ccf8d7c3c75b680e951d492ac8ceb5f30b80a1ff9a6eebac`.

Original lines 574–599:

```python
        # Before publication, not a fabricated published_at/available_at.
        "manifest_prepared_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_allowed": False,
        "buy_gate_updated": False,
        "orders_sent": False,
    }
    manifest_relative = f"panels/{panel_dir.name}/manifest.json"
    if (panel_dir / "manifest.json").exists():
        # Do not retrofit provenance into an already published panel. The normal
        # already_current path returned above without any writes.
        raise StoreError("HK02_IMMUTABLE_MANIFEST_EXISTS")
    _write_json(panel_dir / "manifest.json", manifest)
    _write_json(asset_root / "panel_latest.json", {"manifest_relative": manifest_relative})
    return {
        "status": "READY",
        "already_current": False,
        "through_date": through_date,
        "through_date_code_count": code_count,
        "new_row_count": int(len(enriched)),
        "panel_sha256": panel_sha,
        "manifest_relative": manifest_relative,
        "production_allowed": False,
        "buy_gate_updated": False,
        "orders_sent": False,
    }
```

## ACTIVE_SHARED_PACKAGE/shared_data/hk_0_2.py — original publisher time labels

Full-file SHA256: `67b28323358427a988c08d6ba7aede6d12610ed6925d4ba3a4513934bcb80668`. This is the shared package selected by the active scheduler, distinct from the V5 M06 daily owner.

Original lines 930–933:

```python
    ranked = _score_with_strategies(predict, models, feature_columns).sort_values("score_prob_active", ascending=False).head(100).copy()
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    ranked["trade_date"], ranked["bar_time"] = target_date, "17:30"
    ranked["code"] = ranked["code_norm"]
```

Original lines 946–949:

```python
    ranked["production_allowed"], ranked["lane"] = False, ""
    ranked["d1_snapshot_close_hkd"], ranked["d1_snapshot_prev_close_hkd"] = ranked["close"], ranked["pre_close"]
    ranked["candidate_pool_time"], ranked["data_cutoff"] = "D-1 close", f"{signal_date} close"
    ranked["research_only"], ranked["cannot_confirm"] = True, ""
```

Original lines 1024–1040:

```python
        spec = SourceSpec(
            source_id="hkconnect_0_2_frozen_prob_active",
            role=HK_0_2_ROLE,
            trade_date=target_date,
            market="HK_CONNECT",
            stages=(HK_0_2_STAGE_ID,),
            cutoff_at="17:30:00",
            source_path=source,
            required_columns=("trade_date", "bar_time", "signal_date", "target_date", "rank", "code_norm", "score_prob_active"),
            bar_time_column="bar_time",
            expected_input_sha256=artifact_sha,
            expected_row_count=len(normalized),
            cannot_confirm=reasons,
            provenance=provenance,
        )
        store = SafeRootStore(Path(store_root), AllowlistRegistry({(target_date, HK_0_2_ROLE): (spec,)}))
        outcome = store.replay_file(owner="v3_shared_data", trade_date=target_date, role=HK_0_2_ROLE, source_id=spec.source_id, stage_id=HK_0_2_STAGE_ID)
```

Original lines 1104–1114:

```python
def materialize_frozen_hk_0_2(store_root: Path | str, asset_root: Path | str, *, signal_date: str, target_date: str) -> dict[str, Any]:
    assets = load_frozen_hk_0_2_assets(asset_root)
    security_master, _ = _load_verified_security_master(store_root, signal_date)
    scoring_diagnostics: dict[str, Any] = {}
    rows = score_frozen_hk_0_2(
        asset_root,
        signal_date=signal_date,
        target_date=target_date,
        eligible_codes=security_master.keys(),
        diagnostics=scoring_diagnostics,
    )
```
