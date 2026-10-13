security_master_rows = [
    {
        field: (
            code
            if field == "code"
            else _normalize_security_master_metadata(source.get(field))
            if field != "name"
            else str(source.get("name") or universe.get(code) or "").strip()
        )
        for field in security_fields
    }
    for code in codes
    for source in (snapshots.get(code) or {},)
]

