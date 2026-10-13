"""M11's default assembly entry; no shared dispatcher or ledger mutation."""
from .m11.daily import M11Binding,capture,generate,read_owner_day
__all__=['M11Binding','capture','generate','read_owner_day']
