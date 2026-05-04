"""MailStore query API — shared between IMAP daemon and MailApp V3."""
from typing import Optional, List, Dict

from . import get_connection, tx


def list_emails(project_code: str = None, sender: str = None,
                search: str = None, limit: int = 50, offset: int = 0,
                labels: str = None, mailbox: str = None) -> List[Dict]:
    conn = get_connection()
    conditions = []
    params = []

    if project_code:
        conditions.append("e.project_code = ?")
        params.append(project_code)
    if sender:
        conditions.append("e.sender LIKE ?")
        params.append(f"%{sender}%")
    if labels:
        for label in labels.split(','):
            conditions.append("e.labels LIKE ?")
            params.append(f"%{label.strip()}%")

    # Mailbox filter
    if mailbox == 'inbox':
        conditions.append("(e.labels NOT LIKE '%sent%' AND e.labels NOT LIKE '%draft%')")
    elif mailbox == 'sent':
        conditions.append("e.labels LIKE '%sent%'")
    elif mailbox == 'drafts':
        conditions.append("e.labels LIKE '%draft%'")

    where = " AND ".join(conditions) if conditions else "1=1"

    # Light fields only for list (no body_text/body_html — saves ~2MB per 50 emails)
    fields = "hash, msg_id, date_time, sender, sender_name, recipients, cc, subject, snippet, size, has_attach, labels, thread_id, project_code, stored_path"
    if search:
        rows = conn.execute(f"""
            SELECT e.{fields} FROM emails e
            JOIN fts_emails f ON e.rowid = f.rowid
            WHERE fts_emails MATCH ? AND {where}
            ORDER BY e.date_time DESC LIMIT ? OFFSET ?
        """, (search, *params, limit, offset)).fetchall()
    else:
        rows = conn.execute(f"""
            SELECT {fields} FROM emails e WHERE {where}
            ORDER BY date_time DESC LIMIT ? OFFSET ?
        """, (*params, limit, offset)).fetchall()

    return [_row_to_dict(r) for r in rows]


def get_email(hash_or_id: str) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM emails WHERE hash = ? OR msg_id = ?",
        (hash_or_id, hash_or_id)
    ).fetchone()
    return _row_to_dict(row) if row else None


def get_attachments(email_hash: str) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT a.* FROM attachments a
        JOIN email_attachments ea ON a.hash = ea.file_hash
        WHERE ea.email_hash = ?
    """, (email_hash,)).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_project_emails(project_code: str, limit: int = 100) -> List[Dict]:
    return list_emails(project_code=project_code, limit=limit)


def count_by_project() -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT project_code, COUNT(*) as count
        FROM emails WHERE project_code IS NOT NULL AND project_code != ''
        GROUP BY project_code ORDER BY count DESC
    """).fetchall()
    return [_row_to_dict(r) for r in rows]


def recent_activity(hours: int = 24) -> int:
    conn = get_connection()
    row = conn.execute("""
        SELECT COUNT(*) as c FROM emails
        WHERE datetime(date_time) > datetime('now', ?)
    """, (f'-{hours} hours',)).fetchone()
    return row['c'] if row else 0


def link_to_project(email_hash: str, project_code: str):
    with tx() as db:
        db.execute("UPDATE emails SET project_code = ? WHERE hash = ?",
                   (project_code, email_hash))
        db.execute("""
            INSERT OR IGNORE INTO email_projects (email_hash, project_code, linked_at)
            VALUES (?, ?, datetime('now'))
        """, (email_hash, project_code))


def _row_to_dict(row) -> Optional[Dict]:
    if row is None:
        return None
    return dict(row)
