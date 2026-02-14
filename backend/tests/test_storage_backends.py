import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from svandoc_backend.storage import LocalStorageBackend, S3StorageBackendStub, get_storage_backend


class StorageBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / f"storage-backend-{uuid4().hex}"
        self.test_dir.mkdir(parents=True, exist_ok=False)

        self.previous_storage_backend = os.environ.get("STORAGE_BACKEND")
        self.previous_local_storage_path = os.environ.get("LOCAL_STORAGE_PATH")
        self.previous_s3_bucket = os.environ.get("S3_BUCKET")
        self.previous_s3_stub_storage_path = os.environ.get("S3_STUB_STORAGE_PATH")

    def tearDown(self) -> None:
        if self.previous_storage_backend is None:
            os.environ.pop("STORAGE_BACKEND", None)
        else:
            os.environ["STORAGE_BACKEND"] = self.previous_storage_backend
        if self.previous_local_storage_path is None:
            os.environ.pop("LOCAL_STORAGE_PATH", None)
        else:
            os.environ["LOCAL_STORAGE_PATH"] = self.previous_local_storage_path
        if self.previous_s3_bucket is None:
            os.environ.pop("S3_BUCKET", None)
        else:
            os.environ["S3_BUCKET"] = self.previous_s3_bucket
        if self.previous_s3_stub_storage_path is None:
            os.environ.pop("S3_STUB_STORAGE_PATH", None)
        else:
            os.environ["S3_STUB_STORAGE_PATH"] = self.previous_s3_stub_storage_path

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_factory_returns_local_backend_when_configured(self) -> None:
        local_root = self.test_dir / "local"
        os.environ["STORAGE_BACKEND"] = "local"
        os.environ["LOCAL_STORAGE_PATH"] = str(local_root)

        backend = get_storage_backend()
        self.assertIsInstance(backend, LocalStorageBackend)

        uri = backend.store_document("doc-1", "invoice.pdf", b"pdf")
        stored_file = Path(uri)
        self.assertTrue(stored_file.exists())
        self.assertEqual(stored_file.read_bytes(), b"pdf")

    def test_factory_returns_s3_stub_backend_when_configured(self) -> None:
        s3_root = self.test_dir / "s3-stub"
        os.environ["STORAGE_BACKEND"] = "s3"
        os.environ["S3_BUCKET"] = "bucket-a"
        os.environ["S3_STUB_STORAGE_PATH"] = str(s3_root)

        backend = get_storage_backend()
        self.assertIsInstance(backend, S3StorageBackendStub)

        uri = backend.store_document("doc-2", "receipt.jpg", b"jpg")
        self.assertEqual(uri, "s3://bucket-a/doc-2/receipt.jpg")
        persisted = s3_root / "bucket-a" / "doc-2" / "receipt.jpg"
        self.assertTrue(persisted.exists())
        self.assertEqual(persisted.read_bytes(), b"jpg")

    def test_factory_rejects_unknown_backend(self) -> None:
        os.environ["STORAGE_BACKEND"] = "unknown"
        with self.assertRaises(ValueError):
            get_storage_backend()


if __name__ == "__main__":
    unittest.main()
