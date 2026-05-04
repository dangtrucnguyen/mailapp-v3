"""MailStore — Stockage emails/PJ content-addressed, partagé IMAP daemon + MailApp V3.

Structure:
  data/mailstore/
    mailstore.db            <- SQLite (WAL mode, FTS5)
    emails/XX/YY/XXXXYY.eml <- .eml bruts (hash sha256 -> 2 niv x 256)
    files/XX/YY/XXXXYY.ext  <- PJ deduplicatees (hash sha256 content)
"""

import hashlib
import os
import re
import sqlite3
import threading
import email
from email import policy
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict

# --- Configuration ----------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent / 'data' / 'mailstore'
DB_PATH = BASE_DIR / 'mailstore.db'
EMAILS_DIR = BASE_DIR / 'emails'
FILES_DIR = BASE_DIR / 'files'

_local = threading.local()

# --- Schema ----------------------------------------------------------------
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
PRAGMA cache_size=-64000;

CREATE TABLE IF NOT EXISTS emails (
    hash        TEXT PRIMARY KEY,
    msg_id      TEXT,
    date_time   TEXT NOT NULL,
    sender      TEXT NOT NULL,
    sender_name TEXT,
    recipients  TEXT,
    cc          TEXT,
    subject     TEXT,
    body_text   TEXT,
    body_html   TEXT,
    snippet     TEXT,
    size        INTEGER,
    has_attach  INTEGER DEFAULT 0,
    labels      TEXT,
    thread_id   TEXT,
    project_code TEXT,
    synced_at   TEXT,
    stored_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date_time DESC);
CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender);
CREATE INDEX IF NOT EXISTS idx_emails_project ON emails(project_code);
CREATE INDEX IF NOT EXISTS idx_emails_thread ON emails(thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_msgid ON emails(msg_id);

CREATE TABLE IF NOT EXISTS attachments (
    hash        TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    mime_type   TEXT,
    size        INTEGER,
    stored_path TEXT,
    count       INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS email_attachments (
    email_hash  TEXT NOT NULL REFERENCES emails(hash) ON DELETE CASCADE,
    file_hash   TEXT NOT NULL REFERENCES attachments(hash),
    PRIMARY KEY (email_hash, file_hash)
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_emails USING fts5(
    subject, body_text, sender, sender_name, recipients,
    content='emails', content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS emails_ai AFTER INSERT ON emails BEGIN
    INSERT INTO fts_emails(rowid, subject, body_text, sender, sender_name, recipients)
    VALUES (new.rowid, new.subject, new.body_text, new.sender, new.sender_name, new.recipients);
END;

CREATE TRIGGER IF NOT EXISTS emails_ad AFTER DELETE ON emails BEGIN
    INSERT INTO fts_emails(fts_emails, rowid, subject, body_text, sender, sender_name, recipients)
    VALUES ('delete', old.rowid, old.subject, old.body_text, old.sender, old.sender_name, old.recipients);
END;

CREATE TABLE IF NOT EXISTS projects (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    status      TEXT DEFAULT 'actif',
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS email_projects (
    email_hash  TEXT NOT NULL REFERENCES emails(hash),
    project_code TEXT NOT NULL REFERENCES projects(code),
    linked_at   TEXT,
    PRIMARY KEY (email_hash, project_code)
);

CREATE TABLE IF NOT EXISTS sync_state (
    mailbox     TEXT PRIMARY KEY,
    last_uid    INTEGER,
    last_sync   TEXT
);
"""

PROJECT_PATTERNS = [
    # Format: 24-016A, 26.002, 24016A (2-digit year + 3-4 digit number + optional letter)
    re.compile(r'\b(\d{2}[-.]?\d{3,4}[A-Z]?[a-z]?)\b'),
    # Format: LEVPOM-001, CDT24001 (uppercase prefix + digits)
    re.compile(r'\b([A-Z]{2,5}[-.]?\d{3,6})\b'),
    # Format: PROJET/CHANTIER/AFFAIRE/DOSSIER prefix + code (must contain digits)
    re.compile(r'(?:PROJET|CHANTIER|AFFAIRE|REF|DOSSIER)[:\s]*([A-Z0-9]*[0-9][A-Z0-9][-A-Z0-9]{2,18})', re.I),
]


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_path(h: str, base: Path, ext: str = '') -> Path:
    d = base / h[:2] / h[2:4]
    d.mkdir(parents=True, exist_ok=True)
    return d / (h + ext)


# --- Connection pool -------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()


@contextmanager
def tx():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# --- Attachment extraction -------------------------------------------------
def _extract_attachments(msg) -> List[Dict]:
    results = []
    for part in msg.iter_attachments():
        filename = part.get_filename()
        if filename:
            try:
                payload = part.get_content()
                if isinstance(payload, str):
                    content = payload.encode('utf-8', errors='replace')
                else:
                    content = payload
                if isinstance(content, bytes):
                    results.append({
                        'hash': hash_bytes(content),
                        'filename': filename,
                        'mime_type': part.get_content_type(),
                        'size': len(content),
                        'content': content,
                    })
            except Exception:
                pass
    return results


# --- Email storage ---------------------------------------------------------
def store_email(raw_bytes: bytes, labels: List[str] = None,
                project_code: str = None) -> Dict:
    labels = labels or []
    eml_hash = hash_bytes(raw_bytes)

    conn = get_connection()
    existing = conn.execute("SELECT 1 FROM emails WHERE hash = ?", (eml_hash,)).fetchone()
    if existing:
        return {'hash': eml_hash, 'stored': False, 'reason': 'duplicate'}

    msg = email.message_from_bytes(raw_bytes, policy=policy.default)
    subject = str(msg.get('Subject', '')).strip()
    msg_id = str(msg.get('Message-ID', '')).strip().strip('<>')
    sender = str(msg.get('From', '')).strip()
    recipients = str(msg.get('To', '')).strip()
    cc = str(msg.get('Cc', '')).strip()

    sender_name = ''
    sender_email = sender
    name_match = re.match(r'"?([^"]*)"?\s*<([^>]+)>', sender)
    if name_match:
        sender_name = name_match.group(1).strip()
        sender_email = name_match.group(2).strip()

    date_str = msg.get('Date', '')
    try:
        dt = parsedate_to_datetime(date_str)
        date_iso = dt.isoformat()
    except Exception:
        date_iso = datetime.now(timezone.utc).isoformat()

    body_text = ''
    body_html = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain' and not body_text:
                try:
                    payload = part.get_content()
                    if isinstance(payload, str):
                        body_text = payload
                except Exception:
                    pass
            elif ct == 'text/html' and not body_html:
                try:
                    payload = part.get_content()
                    if isinstance(payload, str):
                        body_html = payload
                except Exception:
                    pass
    else:
        ct = msg.get_content_type()
        try:
            payload = msg.get_content()
            if isinstance(payload, str):
                if ct == 'text/html':
                    body_html = payload
                else:
                    body_text = payload
        except Exception:
            pass

    snippet = body_text[:200].replace('\n', ' ').strip() if body_text else ''

    attachments = _extract_attachments(msg)

    # Store .eml to disk
    eml_path = _hash_path(eml_hash, EMAILS_DIR, '.eml')
    if not eml_path.exists():
        eml_path.write_bytes(raw_bytes)
    stored_path = str(eml_path.relative_to(BASE_DIR.parent))

    # Store attachments to disk (dedup)
    for att in attachments:
        file_path = _hash_path(att['hash'], FILES_DIR)
        if not file_path.exists():
            file_path.write_bytes(att['content'])
        att['stored_path'] = str(file_path.relative_to(BASE_DIR.parent))
        del att['content']

    if not project_code:
        project_code = detect_project(subject, body_text, sender)

    with tx() as db:
        db.execute("""
            INSERT OR IGNORE INTO emails
            (hash, msg_id, date_time, sender, sender_name, recipients, cc,
             subject, body_text, body_html, snippet, size, has_attach,
             labels, thread_id, project_code, synced_at, stored_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            eml_hash, msg_id, date_iso, sender_email, sender_name,
            recipients, cc, subject, body_text, body_html, snippet,
            len(raw_bytes), 1 if attachments else 0,
            '\n'.join(labels), '', project_code,
            datetime.now(timezone.utc).isoformat(), stored_path
        ))
        for att in attachments:
            db.execute("""
                INSERT OR IGNORE INTO attachments (hash, filename, mime_type, size, stored_path)
                VALUES (?, ?, ?, ?, ?)
            """, (att['hash'], att['filename'], att['mime_type'], att['size'], att['stored_path']))
            db.execute("""
                INSERT OR IGNORE INTO email_attachments (email_hash, file_hash)
                VALUES (?, ?)
            """, (eml_hash, att['hash']))

    return {
        'hash': eml_hash, 'stored': True,
        'subject': subject, 'sender': sender_email, 'date': date_iso,
        'attachments': len(attachments), 'project_code': project_code,
    }


# --- Project detection -----------------------------------------------------
def detect_project(subject: str = '', body: str = '', sender: str = '') -> Optional[str]:
    text = f"{subject} {body[:1000]}"
    for pattern in PROJECT_PATTERNS:
        match = pattern.search(text)
        if match:
            code = match.group(1).replace('.', '-').upper()
            return code
    return None


# --- Stats -----------------------------------------------------------------
def stats() -> Dict:
    conn = get_connection()
    return {
        'total_emails': conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0],
        'total_attachments': conn.execute("SELECT COUNT(*) FROM attachments").fetchone()[0],
        'total_size': conn.execute(
            "SELECT COALESCE(SUM(size), 0) FROM emails"
        ).fetchone()[0],
        'project_count': conn.execute(
            "SELECT COUNT(DISTINCT project_code) FROM emails WHERE project_code != ''"
        ).fetchone()[0],
    }
