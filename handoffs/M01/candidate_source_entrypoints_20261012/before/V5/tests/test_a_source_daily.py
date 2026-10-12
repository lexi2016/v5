
import pytest
from v5_shadow.a_source_daily import validate_date, M01BindingError

def test_date_ok():
    assert validate_date('20261011') == '20261011'

def test_bad_date():
    with pytest.raises(M01BindingError):
        validate_date('20260230')
