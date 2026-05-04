"""MailApp V3 — Initialisation base de données"""
import aiosqlite
import os
from config import DATABASE, DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    role TEXT NOT NULL DEFAULT 'utilisateur',  -- admin, manager, utilisateur
    contact_id INTEGER,
    is_active INTEGER DEFAULT 1,
    avatar_url TEXT,
    last_login TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS projects (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'En cours',
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS project_members (
    project_code TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'lecteur',
    -- chef, collaborateur, lecteur
    can_create_tasks INTEGER DEFAULT 1,
    can_assign_tasks INTEGER DEFAULT 0,
    can_upload_docs INTEGER DEFAULT 1,
    can_validate_docs INTEGER DEFAULT 0,
    can_manage_members INTEGER DEFAULT 0,
    can_send_emails INTEGER DEFAULT 1,
    invited_by INTEGER,
    joined_at TEXT DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (project_code, user_id),
    FOREIGN KEY (project_code) REFERENCES projects(code),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    contact_id INTEGER,
    invited_by INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    role TEXT DEFAULT 'utilisateur',
    expires_at TEXT,
    accepted_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (invited_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_permissions (
    user_id INTEGER NOT NULL,
    module TEXT NOT NULL,
    permission TEXT NOT NULL,     -- read, write, send, manage
    granted INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, module, permission),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Table sessions (pour invalidation)
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- PHASE 2: Emails (sync depuis Gmail)
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,              -- message_id Gmail
    thread_id TEXT,
    subject TEXT,
    sender TEXT NOT NULL,
    recipients TEXT,
    cc TEXT,
    body_text TEXT,
    body_html TEXT,
    date_time TEXT NOT NULL,
    has_attachments INTEGER DEFAULT 0,
    is_read INTEGER DEFAULT 1,
    is_archived INTEGER DEFAULT 0,
    labels TEXT,                       -- JSON array
    project_code TEXT,
    synced_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (project_code) REFERENCES projects(code)
);

-- PHASE 2: Tâches
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,         -- T-0001, T-0002...
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'A faire',     -- A faire, En cours, En attente, Termine
    priority TEXT DEFAULT 'Normale',   -- Basse, Normale, Haute, Urgente
    due_date TEXT,
    project_code TEXT NOT NULL,
    assigned_to INTEGER,
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (project_code) REFERENCES projects(code),
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- PHASE 2: Documents
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    size INTEGER,
    mime_type TEXT,
    version INTEGER DEFAULT 1,
    author_id INTEGER,
    project_code TEXT,
    email_source_id TEXT,
    task_id INTEGER,
    description TEXT,
    status TEXT DEFAULT 'En cours',    -- Brouillon, En cours, Valide, Obsolete
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (author_id) REFERENCES users(id),
    FOREIGN KEY (project_code) REFERENCES projects(code),
    FOREIGN KEY (email_source_id) REFERENCES emails(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- PHASE 2: Versions de documents
CREATE TABLE IF NOT EXISTS document_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    stored_path TEXT NOT NULL,
    size INTEGER,
    uploaded_by INTEGER,
    comment TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (document_id) REFERENCES documents(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

-- PHASE 2: Tables pivot d'interconnexion
CREATE TABLE IF NOT EXISTS email_tasks (
    email_id TEXT NOT NULL,
    task_id INTEGER NOT NULL,
    PRIMARY KEY (email_id, task_id),
    FOREIGN KEY (email_id) REFERENCES emails(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE IF NOT EXISTS task_documents (
    task_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    PRIMARY KEY (task_id, document_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS project_documents (
    project_code TEXT NOT NULL,
    document_id INTEGER NOT NULL,
    PRIMARY KEY (project_code, document_id),
    FOREIGN KEY (project_code) REFERENCES projects(code),
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- PHASE 2: Contacts
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    company TEXT,
    role TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- PHASE 2: Commentaires (sur tâches et documents)
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,         -- 'task' ou 'document'
    entity_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Phase 3: Drafts & Sent
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    to_email TEXT DEFAULT '',
    cc TEXT DEFAULT '',
    bcc TEXT DEFAULT '',
    subject TEXT DEFAULT '',
    body_text TEXT DEFAULT '',
    body_html TEXT DEFAULT '',
    reply_to_email_id TEXT,
    reply_to_message_id TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sent_emails (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    to_email TEXT DEFAULT '',
    cc TEXT DEFAULT '',
    subject TEXT DEFAULT '',
    body_text TEXT DEFAULT '',
    body_html TEXT DEFAULT '',
    reply_to_message_id TEXT,
    sent_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Phase 5: Push notifications & Webhooks
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    endpoint TEXT NOT NULL,
    subscription_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    project_code TEXT,
    events TEXT NOT NULL DEFAULT 'task.created,task.updated',  -- JSON array or comma-separated
    secret TEXT,
    is_active INTEGER DEFAULT 1,
    created_by INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (project_code) REFERENCES projects(code)
);

CREATE TABLE IF NOT EXISTS webhook_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    status_code INTEGER,
    response_body TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (webhook_id) REFERENCES webhooks(id) ON DELETE CASCADE
);

-- Index Phase 2+3
CREATE INDEX IF NOT EXISTS idx_emails_project ON emails(project_code);
CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender);
CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date_time);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_code);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_code);
CREATE INDEX IF NOT EXISTS idx_documents_task ON documents(task_id);
CREATE INDEX IF NOT EXISTS idx_comments_entity ON comments(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_project_members_user ON project_members(user_id);
CREATE INDEX IF NOT EXISTS idx_project_members_project ON project_members(project_code);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(email);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
"""

async def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(SCHEMA)
        await db.commit()
    print(f"✅ Database initialized: {DATABASE}")

async def get_db():
    db = await aiosqlite.connect(DATABASE)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db

def get_sync_db():
    """Version synchrone pour les cas simples (templates)"""
    import sqlite3
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db

def get_next_task_code(db):
    """Genere le prochain code tache (T-0001, T-0002...)"""
    import sqlite3
    db.execute("BEGIN IMMEDIATE")
    row = db.execute("SELECT MAX(CAST(SUBSTR(code, 3) AS INTEGER)) FROM tasks").fetchone()
    num = (row[0] or 0) + 1
    return f"T-{num:04d}"
