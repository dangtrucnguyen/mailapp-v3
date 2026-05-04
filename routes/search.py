"""Unified search across emails, projects, documents, attachments."""
from fastapi import APIRouter, Request, HTTPException
from typing import Optional
from .auth import get_current_user

router = APIRouter(prefix='/api/search', tags=['search'])


def _mailstore_available():
    try:
        from mailstore import get_connection
        get_connection()
        return True
    except Exception:
        return False


@router.get('')
async def unified_search(request: Request):
    """Search across all categories. Query params: q, limit (default 5 per category)."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    q = (request.query_params.get('q', '') or '').strip()
    if not q or len(q) < 2:
        return {'results': []}

    limit = int(request.query_params.get('limit', '5'))

    results = []

    if _mailstore_available():
        from mailstore import get_connection
        conn = get_connection()

        # --- Emails (FTS5 full-text) ---
        try:
            rows = conn.execute("""
                SELECT e.hash, e.subject, e.sender, e.sender_name, e.date_time,
                       e.snippet, e.has_attach, e.labels, e.project_code,
                       snippet(fts_emails, 0, '<b>', '</b>', '...', 40) as highlight
                FROM emails e
                JOIN fts_emails f ON e.rowid = f.rowid
                WHERE fts_emails MATCH ?
                ORDER BY e.date_time DESC LIMIT ?
            """, (q, limit)).fetchall()
            for r in rows:
                results.append({
                    'category': 'emails',
                    'id': r['hash'],
                    'title': r['subject'] or '(sans sujet)',
                    'subtitle': r['sender_name'] or r['sender'],
                    'date': r['date_time'],
                    'snippet': r['snippet'] or '',
                    'highlight': r['highlight'] or '',
                    'has_attachments': r['has_attach'],
                    'project_code': r['project_code'],
                    'labels': r['labels'],
                })
        except Exception as e:
            # FTS5 might fail on special chars — fallback to LIKE
            try:
                rows = conn.execute("""
                    SELECT hash, subject, sender, sender_name, date_time,
                           snippet, has_attach, labels, project_code
                    FROM emails
                    WHERE subject LIKE ? OR sender LIKE ? OR recipients LIKE ?
                    ORDER BY date_time DESC LIMIT ?
                """, (f'%{q}%', f'%{q}%', f'%{q}%', limit)).fetchall()
                for r in rows:
                    results.append({
                        'category': 'emails',
                        'id': r['hash'],
                        'title': r['subject'] or '(sans sujet)',
                        'subtitle': r['sender_name'] or r['sender'],
                        'date': r['date_time'],
                        'snippet': r['snippet'] or '',
                        'highlight': '',
                        'has_attachments': r['has_attach'],
                        'project_code': r['project_code'],
                        'labels': r['labels'],
                    })
            except Exception:
                pass

        # --- Projects ---
        try:
            rows = conn.execute("""
                SELECT code, name, description, status
                FROM projects
                WHERE code LIKE ? OR name LIKE ? OR description LIKE ?
                ORDER BY code LIMIT ?
            """, (f'%{q}%', f'%{q}%', f'%{q}%', limit)).fetchall()
            for r in rows:
                # Count emails in this project
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM emails WHERE project_code = ?",
                    (r['code'],)
                ).fetchone()[0]
                results.append({
                    'category': 'projects',
                    'id': r['code'],
                    'title': r['name'] or r['code'],
                    'subtitle': r['description'] or '',
                    'status': r['status'],
                    'email_count': cnt,
                })
        except Exception:
            pass

        # --- Pièces jointes ---
        try:
            rows = conn.execute("""
                SELECT a.hash, a.filename, a.mime_type, a.size,
                       e.subject, e.hash as email_hash
                FROM attachments a
                JOIN email_attachments ea ON a.hash = ea.file_hash
                JOIN emails e ON ea.email_hash = e.hash
                WHERE a.filename LIKE ?
                ORDER BY a.filename LIMIT ?
            """, (f'%{q}%', limit)).fetchall()
            for r in rows:
                results.append({
                    'category': 'attachments',
                    'id': r['hash'],
                    'title': r['filename'],
                    'subtitle': r['subject'] or '',
                    'mime_type': r['mime_type'],
                    'size': r['size'],
                    'email_hash': r['email_hash'],
                })
        except Exception:
            pass

        # --- Documents (mailstore doesn't have docs yet, skip) ---
        # TODO: add document search when doc storage exists

    return {'results': results, 'query': q}
