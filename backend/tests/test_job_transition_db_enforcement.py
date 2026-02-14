import os
import shutil
import unittest
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


class JobTransitionDatabaseEnforcementTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_tmp = Path("tests_tmp")
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        self.test_dir = workspace_tmp / "job-transition-db"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        self.test_dir.mkdir(parents=True, exist_ok=False)
        self.db_path = self.test_dir / "job-transitions.db"
        self.db_url = f"sqlite:///{self.db_path.as_posix()}"

        self.previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = self.db_url

        cfg = Config("alembic.ini")
        cfg.set_main_option("script_location", "alembic")
        command.upgrade(cfg, "head")

        self.engine = sa.create_engine(self.db_url)
        self._seed_rows()

    def tearDown(self) -> None:
        self.engine.dispose()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _seed_rows(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO documents (
                        id, team_id, uploaded_by, filename, mime_type, checksum, storage_uri, page_count
                    )
                    VALUES (
                        :id, :team_id, :uploaded_by, :filename, :mime_type, :checksum, :storage_uri, :page_count
                    )
                    """
                ),
                {
                    "id": "doc-db-1",
                    "team_id": "team-db",
                    "uploaded_by": "user-db",
                    "filename": "invoice.pdf",
                    "mime_type": "application/pdf",
                    "checksum": "db-checksum-1",
                    "storage_uri": "/tmp/invoice.pdf",
                    "page_count": 1,
                },
            )
            conn.execute(
                sa.text("INSERT INTO jobs (id, document_id, status) VALUES (:id, :document_id, :status)"),
                {
                    "id": "job-db-1",
                    "document_id": "doc-db-1",
                    "status": "queued",
                },
            )

    def test_valid_transition_is_allowed_by_trigger(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                sa.text("UPDATE jobs SET status = 'processing' WHERE id = :job_id"),
                {"job_id": "job-db-1"},
            )

        with self.engine.connect() as conn:
            status = conn.execute(
                sa.text("SELECT status FROM jobs WHERE id = :job_id"),
                {"job_id": "job-db-1"},
            ).scalar_one()
        self.assertEqual(status, "processing")

    def test_invalid_transition_is_rejected_by_trigger(self) -> None:
        with self.assertRaises(sa.exc.DBAPIError) as ctx:
            with self.engine.begin() as conn:
                conn.execute(
                    sa.text("UPDATE jobs SET status = 'completed' WHERE id = :job_id"),
                    {"job_id": "job-db-1"},
                )

        self.assertIn("invalid_jobs_status_transition", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
