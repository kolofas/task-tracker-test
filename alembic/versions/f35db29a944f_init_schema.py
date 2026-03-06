"""init schema + seed demo data

Revision ID: f35db29a944f
Revises:
Create Date: 2026-03-05 23:59:00.475510
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f35db29a944f"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) schema
    op.execute(
        """
        CREATE TABLE users (
            id          BIGSERIAL PRIMARY KEY,
            name        TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE projects (
            id          BIGSERIAL PRIMARY KEY,
            name        TEXT NOT NULL,
            owner_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE project_members (
            project_id  BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            joined_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (project_id, user_id)
        );

        CREATE TABLE tasks (
            id          BIGSERIAL PRIMARY KEY,
            project_id  BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

            title       TEXT NOT NULL,
            description TEXT,

            priority    TEXT NOT NULL,
            status      TEXT NOT NULL,

            author_id   BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            assignee_id BIGINT REFERENCES users(id) ON DELETE SET NULL,

            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT chk_tasks_priority
                CHECK (priority IN ('low','medium','high','critical')),

            CONSTRAINT chk_tasks_status
                CHECK (status IN ('created','in_progress','review','done','cancelled'))
        );

        CREATE TABLE task_status_history (
            id          BIGSERIAL PRIMARY KEY,
            task_id     BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,

            from_status TEXT NOT NULL,
            to_status   TEXT NOT NULL,

            changed_by  BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT chk_hist_from_status
                CHECK (from_status IN ('created','in_progress','review','done','cancelled')),

            CONSTRAINT chk_hist_to_status
                CHECK (to_status IN ('created','in_progress','review','done','cancelled'))
        );

        CREATE INDEX ix_tasks_project_id ON tasks(project_id);
        CREATE INDEX ix_tasks_status_priority ON tasks(status, priority);
        CREATE INDEX ix_tasks_assignee_id ON tasks(assignee_id);
        CREATE INDEX ix_task_status_history_task_changed_at
            ON task_status_history(task_id, changed_at DESC);
        """
    )

    # 2) seed minimal demo data so /tasks works out of the box
    op.execute(
        """
        INSERT INTO users (id, name, created_at)
        VALUES (1, 'Demo User', now())
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO projects (id, name, owner_id, created_at)
        VALUES (1, 'Demo Project', 1, now())
        ON CONFLICT (id) DO NOTHING;

        INSERT INTO project_members (project_id, user_id, joined_at)
        VALUES (1, 1, now())
        ON CONFLICT (project_id, user_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS task_status_history;
        DROP TABLE IF EXISTS tasks;
        DROP TABLE IF EXISTS project_members;
        DROP TABLE IF EXISTS projects;
        DROP TABLE IF EXISTS users;
        """
    )