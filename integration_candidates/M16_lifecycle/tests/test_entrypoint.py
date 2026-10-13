import importlib.util
import unittest

class EntrypointTests(unittest.TestCase):
    def test_default_entrypoint_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.m16_runtime'),
                             'M16 has no isolated default runtime entrypoint')

if __name__ == '__main__': unittest.main()
