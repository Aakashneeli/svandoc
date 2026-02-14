import os
import unittest
from unittest.mock import patch

from svandoc_backend.db import DEFAULT_DATABASE_URL, get_database_url, normalize_database_url


class DatabaseConfigTests(unittest.TestCase):
    def test_normalize_database_url_promotes_psycopg_driver(self) -> None:
        raw = "postgresql://user:pass@localhost:5432/sample"
        self.assertEqual(
            normalize_database_url(raw),
            "postgresql+psycopg://user:pass@localhost:5432/sample",
        )

    def test_normalize_database_url_keeps_explicit_driver(self) -> None:
        raw = "postgresql+psycopg://user:pass@localhost:5432/sample"
        self.assertEqual(normalize_database_url(raw), raw)

    def test_get_database_url_uses_default_when_env_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                get_database_url(),
                "postgresql+psycopg://postgres:postgres@localhost:5432/svandoc",
            )

    def test_get_database_url_reads_environment_variable(self) -> None:
        with patch.dict(os.environ, {"DATABASE_URL": DEFAULT_DATABASE_URL}, clear=True):
            self.assertEqual(
                get_database_url(),
                "postgresql+psycopg://postgres:postgres@localhost:5432/svandoc",
            )


if __name__ == "__main__":
    unittest.main()
