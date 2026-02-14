"""Enforce valid job status transitions at DB level.

Revision ID: 20260214_0004
Revises: 20260214_0003
Create Date: 2026-02-14
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260214_0004"
down_revision = "20260214_0003"
branch_labels = None
depends_on = None

TRANSITION_CONDITION_SQL = """
(
    (OLD.status = 'queued' AND NEW.status IN ('processing', 'failed')) OR
    (OLD.status = 'processing' AND NEW.status IN ('review_required', 'completed', 'failed')) OR
    (OLD.status = 'review_required' AND NEW.status IN ('processing', 'completed', 'failed')) OR
    (OLD.status = 'failed' AND NEW.status = 'queued')
)
"""


def _upgrade_postgresql() -> None:
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION enforce_jobs_status_transition()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.status IS DISTINCT FROM OLD.status THEN
                IF NOT {TRANSITION_CONDITION_SQL} THEN
                    RAISE EXCEPTION 'invalid_jobs_status_transition: % -> %', OLD.status, NEW.status;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_jobs_status_transition ON jobs;")
    op.execute(
        """
        CREATE TRIGGER trg_jobs_status_transition
        BEFORE UPDATE OF status ON jobs
        FOR EACH ROW
        EXECUTE FUNCTION enforce_jobs_status_transition();
        """
    )


def _upgrade_sqlite() -> None:
    op.execute(
        f"""
        CREATE TRIGGER trg_jobs_status_transition
        BEFORE UPDATE OF status ON jobs
        FOR EACH ROW
        WHEN NEW.status <> OLD.status
        BEGIN
            SELECT CASE
                WHEN {TRANSITION_CONDITION_SQL} THEN 1
                ELSE RAISE(ABORT, 'invalid_jobs_status_transition')
            END;
        END;
        """
    )


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        _upgrade_postgresql()
        return
    if dialect == "sqlite":
        _upgrade_sqlite()
        return
    raise RuntimeError(f"Unsupported dialect for job transition trigger migration: {dialect}")


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_jobs_status_transition ON jobs;")
        op.execute("DROP FUNCTION IF EXISTS enforce_jobs_status_transition();")
        return
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_jobs_status_transition;")
        return
    raise RuntimeError(f"Unsupported dialect for job transition trigger migration downgrade: {dialect}")
