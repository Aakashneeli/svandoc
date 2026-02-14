import unittest

from svandoc_backend import __version__


class BackendSanityTests(unittest.TestCase):
    def test_version_is_defined(self) -> None:
        self.assertIsInstance(__version__, str)
        self.assertTrue(__version__)


if __name__ == "__main__":
    unittest.main()
