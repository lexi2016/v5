def _normalize_security_master_metadata(value: Any) -> Any:
    """
    Normalize optional security-master metadata before canonical hashing.

    - None stays None
    - NaN/NaT-like missing values become JSON null
    - finite values and strings are preserved
    - infinity remains invalid
    """
    if value is None:
        return None

    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            raise ValueError("HK_SECURITY_MASTER_INFINITE_METADATA")
        return value

    if type(value).__name__ in {"NAType", "NaTType"}:
        return None

    return value

