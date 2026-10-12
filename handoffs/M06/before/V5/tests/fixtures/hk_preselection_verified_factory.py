from V5.tests.fixtures.hk_pool_factory import create_hk_reader_fixture

def create_verified_fixture(root):
    return create_hk_reader_fixture(root,target='20261008',signal='20261007',eligibility='20260930')
