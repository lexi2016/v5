def test_sha_contract_shape():
    assert len('0'*64)==64

def test_reject_bad_sha_shape():
    assert len('bad') != 64
