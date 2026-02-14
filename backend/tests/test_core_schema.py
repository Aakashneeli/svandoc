import unittest

import sqlalchemy as sa

from svandoc_backend.db import Base
import svandoc_backend.models  # noqa: F401


class CoreSchemaModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = sa.create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.inspector = sa.inspect(self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_core_tables_exist(self) -> None:
        table_names = set(self.inspector.get_table_names())
        self.assertIn("documents", table_names)
        self.assertIn("jobs", table_names)
        self.assertIn("extraction_results", table_names)
        self.assertIn("user_corrections", table_names)
        self.assertIn("export_artifacts", table_names)

    def test_documents_constraints_and_indexes_exist(self) -> None:
        unique_names = {item["name"] for item in self.inspector.get_unique_constraints("documents")}
        check_names = {item["name"] for item in self.inspector.get_check_constraints("documents")}
        index_names = {item["name"] for item in self.inspector.get_indexes("documents")}

        self.assertIn("uq_documents_checksum", unique_names)
        self.assertIn("ck_documents_page_count_positive", check_names)
        self.assertIn("ix_documents_team_id", index_names)
        self.assertIn("ix_documents_created_at", index_names)

    def test_jobs_constraints_and_indexes_exist(self) -> None:
        check_names = {item["name"] for item in self.inspector.get_check_constraints("jobs")}
        index_names = {item["name"] for item in self.inspector.get_indexes("jobs")}
        foreign_keys = self.inspector.get_foreign_keys("jobs")

        self.assertIn("ck_jobs_attempt_count_non_negative", check_names)
        self.assertIn("ck_jobs_status_valid", check_names)
        self.assertIn("ix_jobs_document_id", index_names)
        self.assertIn("ix_jobs_status", index_names)
        self.assertIn("ix_jobs_created_at", index_names)
        self.assertTrue(any(fk["referred_table"] == "documents" for fk in foreign_keys))

    def test_extraction_results_constraints_and_indexes_exist(self) -> None:
        unique_names = {item["name"] for item in self.inspector.get_unique_constraints("extraction_results")}
        check_names = {item["name"] for item in self.inspector.get_check_constraints("extraction_results")}
        index_names = {item["name"] for item in self.inspector.get_indexes("extraction_results")}
        foreign_keys = self.inspector.get_foreign_keys("extraction_results")

        self.assertIn("uq_extraction_results_document_id", unique_names)
        self.assertIn("ck_extraction_results_doc_type_valid", check_names)
        self.assertIn("ix_extraction_results_doc_type", index_names)
        self.assertIn("ix_extraction_results_review_required", index_names)
        self.assertTrue(any(fk["referred_table"] == "documents" for fk in foreign_keys))

    def test_user_corrections_indexes_and_foreign_key_exist(self) -> None:
        index_names = {item["name"] for item in self.inspector.get_indexes("user_corrections")}
        foreign_keys = self.inspector.get_foreign_keys("user_corrections")

        self.assertIn("ix_user_corrections_document_id", index_names)
        self.assertIn("ix_user_corrections_corrected_at", index_names)
        self.assertTrue(any(fk["referred_table"] == "documents" for fk in foreign_keys))

    def test_export_artifacts_constraints_indexes_and_foreign_key_exist(self) -> None:
        check_names = {item["name"] for item in self.inspector.get_check_constraints("export_artifacts")}
        index_names = {item["name"] for item in self.inspector.get_indexes("export_artifacts")}
        foreign_keys = self.inspector.get_foreign_keys("export_artifacts")

        self.assertIn("ck_export_artifacts_format_valid", check_names)
        self.assertIn("ix_export_artifacts_document_id", index_names)
        self.assertIn("ix_export_artifacts_created_at", index_names)
        self.assertTrue(any(fk["referred_table"] == "documents" for fk in foreign_keys))


if __name__ == "__main__":
    unittest.main()
