import pytest
from v5_shadow.a_source_daily import validate_date,M01BindingError
def test_valid(): assert validate_date('20261011')=='20261011'
def test_invalid(): 
    with pytest.raises(M01BindingError): validate_date('20260230')
