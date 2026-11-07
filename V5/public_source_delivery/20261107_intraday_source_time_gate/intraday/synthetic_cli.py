"""Test harness ONLY. Mock loader is not an alternate production source adapter."""
from synthetic_fixture import install
import observation_api
if __name__=='__main__':
 with install():observation_api.main()
