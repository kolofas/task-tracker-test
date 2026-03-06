CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
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

-- project_members необходимая таблица, потому что связь между users и projects является many-to-many,
-- поэтому используется таблица-связка в лице project-members, в которой каждая запись фиксирует участие
-- пользователя в проекте. Композитный primary key (project_id, user_id) предотвратит дубль участия

-- projects содержит owner_id, потому что у каждого проекта есть один владеле.
-- Это реализовано через внешний ключ на users.

-- tasks содержит project_id, потому что каждая задача принадлежит конкретному проекту.
-- Также в таблице есть author_id и assignee_id - автор задачи и исполнитель,
-- что позволяет разделять ответственность за создание и выполнение задачи.

-- статус задачи хранится непосредственно в tasks,
-- чтобы можно было быстро фильтровать задачи по статусу
-- без необходимости вычислять его из истории изменений.

-- task_status_history хранит историю изменения статусов задачи.
-- Каждая запись фиксирует переход from_status -> to_status,
-- пользователя, который сделал изменений (changed_by),
-- и время изменения (changed_at).
-- Это позволяет реализовать аудит изменений и восстановить историю работы над задачей

-- индекс на tasks(project_id) нужен для быстрого получения задач конкретного проекта

-- индекс на tasks(status, priority) ускоряет фильтрацию задач по статусу и приоритету,
-- что соответствует API запросу /tasks?status=&priority=

-- индекс на tasks(assignee_id) позволяет быстро находить задачи,
-- назначенные конкретному пользователю

-- индекс на task_status_history(task_id, changed_at) ускоряет получение истории
-- изменения статусов конкретной задачи в хронологическом порядке