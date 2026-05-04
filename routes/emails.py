"""MailApp V3 — Routes Email (API JSON + pages fallback)
Lit depuis mailstore (nouveau) avec fallback sur l'ancienne DB."""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.templating import Jinja2Templates

from routes.auth import get_current_user
from database import get_sync_db
from services.smtp import send_email
import config

router = APIRouter(prefix='/api/emails', tags=['emails'])
templates = Jinja2Templates(directory='templates')


# --- Helpers ----------------------------------------------------------------
def _mailstore_available():
    """Check if mailstore DB is populated."""
    try:
        from mailstore.query import recent_activity
        return recent_activity(24 * 365) > 0  # any email in last year?
    except Exception:
        return False


def _row_to_dict_email(row, db_type='legacy'):
    """Normalize email dict regardless of source."""
    if db_type == 'mailstore':
        return {
            'id': row['hash'],
            'hash': row['hash'],
            'subject': row.get('subject', ''),
            'sender': row.get('sender', ''),
            'sender_name': row.get('sender_name', ''),
            'recipients': row.get('recipients', ''),
            'date_time': row.get('date_time', ''),
            'body_text': row.get('body_text', ''),
            'body_html': row.get('body_html', ''),
            'snippet': row.get('snippet', ''),
            'has_attachments': row.get('has_attach', 0),
            'labels': row.get('labels', ''),
            'project_code': row.get('project_code', ''),
            'project_name': row.get('project_name', ''),
            'is_read': 0,  # mailstore doesn't track read state yet
        }
    else:
        d = dict(row) if row else {}
        d['id'] = d.get('id', '')
        return d


# --- Liste emails (JSON) ---------------------------------------------------
@router.get('')
@router.get('/')
async def emails_list_json(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 50))
    offset = (page - 1) * limit
    search = request.query_params.get('search', '')
    project = request.query_params.get('project', '')
    mailbox = request.query_params.get('mailbox', 'inbox')  # inbox | sent | drafts | all

    # Try mailstore first
    if _mailstore_available():
        from mailstore.query import list_emails as ms_list, count_by_project
        rows = ms_list(
            project_code=project or None,
            search=search or None,
            limit=limit, offset=offset,
            mailbox=mailbox
        )
        emails = [_row_to_dict_email(r, 'mailstore') for r in rows]
        # Get project names
        if emails:
            from mailstore import get_connection as ms_conn
            conn = ms_conn()
            for e in emails:
                if e.get('project_code'):
                    p = conn.execute(
                        "SELECT name FROM projects WHERE code = ?",
                        (e['project_code'],)
                    ).fetchone()
                    if p:
                        e['project_name'] = p['name']
        return {'emails': emails}

    # Fallback: old DB
    db = get_sync_db()
    try:
        rows = db.execute(
            'SELECT e.*, p.name as project_name FROM emails e '
            'LEFT JOIN projects p ON e.project_code = p.code '
            'ORDER BY e.date_time DESC LIMIT ? OFFSET ?',
            (limit, offset)
        ).fetchall()
        return {'emails': [_row_to_dict_email(r, 'legacy') for r in rows]}
    finally:
        db.close()


# --- Detail email ----------------------------------------------------------
@router.get('/{email_id}')
async def email_detail_json(request: Request, email_id: str):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    # Try mailstore first
    if _mailstore_available():
        from mailstore.query import get_email as ms_get, get_attachments
        email = ms_get(email_id)
        if email:
            result = _row_to_dict_email(email, 'mailstore')
            result['attachments'] = get_attachments(email['hash'])
            result['linked_tasks'] = []  # TODO: tasks from mailstore
            return {'email': result}

    # Fallback: old DB
    db = get_sync_db()
    try:
        email = db.execute('SELECT * FROM emails WHERE id = ?', (email_id,)).fetchone()
        if not email:
            raise HTTPException(404)
        email = dict(email)
        linked_tasks = db.execute(
            'SELECT t.*, u.display_name as assignee_name FROM tasks t '
            'JOIN email_tasks et ON t.id = et.task_id '
            'LEFT JOIN users u ON t.assigned_to = u.id '
            'WHERE et.email_id = ?', (email_id,)
        ).fetchall()
        email['linked_tasks'] = [dict(t) for t in linked_tasks]
        return {'email': email}
    finally:
        db.close()


# --- Inline images (cid:) ---------------------------------------------------
@router.get('/{email_id}/inline/{cid:path}')
async def inline_image(request: Request, email_id: str, cid: str):
    """Serve inline images referenced by cid: in HTML body.
    Parses the raw .eml to extract the matching Content-ID part."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    import email as em
    from pathlib import Path
    from mailstore import BASE_DIR as MS_BASE

    # Find the .eml file for this email
    from mailstore.query import get_email as ms_get
    email_data = ms_get(email_id)
    if not email_data:
        raise HTTPException(404)

    stored_path = email_data.get('stored_path', '')
    eml_path = Path(MS_BASE).parent / stored_path
    if not eml_path.exists():
        raise HTTPException(404)

    # Parse the raw .eml and find the part with matching Content-ID
    msg = em.message_from_bytes(eml_path.read_bytes(), policy=em.policy.default)

    def find_part_with_cid(node, target_cid):
        if node.is_multipart():
            for sub in node.get_payload():
                result = find_part_with_cid(sub, target_cid)
                if result:
                    return result
        else:
            node_cid = node.get('Content-ID', '').strip('<>')
            if node_cid == target_cid or node_cid == f'{target_cid}':
                return node
        return None

    part = find_part_with_cid(msg, cid)
    if not part:
        # Try with angle brackets
        part = find_part_with_cid(msg, f'<{cid}>')
    if not part:
        raise HTTPException(404, f"CID not found: {cid}")

    content = part.get_content()
    if isinstance(content, str):
        content = content.encode('utf-8', errors='replace')

    content_type = part.get_content_type()
    if not content_type.startswith('image/'):
        content_type = 'image/png'

    return JSONResponse(
        content={'data': content.hex(), 'mime': content_type},
        media_type='application/json'
    )


# --- Inline image as base64 data URI (convenience) -------------------------
@router.get('/{email_id}/body-html')
async def email_body_html(request: Request, email_id: str):
    """Return body_html with cid: references replaced by inline data URIs."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    import email as em
    import re
    import base64
    from pathlib import Path
    from mailstore import BASE_DIR as MS_BASE
    from mailstore.query import get_email as ms_get

    email_data = ms_get(email_id)
    if not email_data:
        raise HTTPException(404)

    html = email_data.get('body_html', '')
    if not html or 'cid:' not in html:
        return {'html': html or '', 'has_cid': False}

    # Load .eml to extract inline images
    stored_path = email_data.get('stored_path', '')
    eml_path = Path(MS_BASE).parent / stored_path
    cid_map = {}

    if eml_path.exists():
        msg = em.message_from_bytes(eml_path.read_bytes(), policy=em.policy.default)
        for part in msg.walk():
            if part.is_multipart():
                continue
            cid = part.get('Content-ID', '').strip('<>')
            if cid:
                try:
                    content = part.get_content()
                    if isinstance(content, str):
                        content = content.encode('utf-8')
                    if isinstance(content, bytes) and len(content) < 5_000_000:
                        b64 = base64.b64encode(content).decode()
                        mime = part.get_content_type()
                        cid_map[cid] = f'data:{mime};base64,{b64}'
                except Exception:
                    pass

    # Replace cid: references
    def replace_cid(match):
        cid_ref = match.group(1)
        # Try exact match first, then without angle brackets
        if cid_ref in cid_map:
            return cid_map[cid_ref]
        # Try common variations
        for key, val in cid_map.items():
            if key == cid_ref or cid_ref in key or key in cid_ref:
                return val
        return match.group(0)  # keep original if not found

    html = re.sub(r'cid:([^"\'\s>)]+)', replace_cid, html)
    return {'html': html, 'has_cid': True, 'cids_mapped': len(cid_map)}
@router.post('/send')
async def api_send(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    body = await request.json()
    to = body.get('to', '').strip()
    subject = body.get('subject', '').strip()
    text = body.get('body', '').strip()
    cc = body.get('cc', '').strip()
    draft_id = body.get('draft_id')
    reply_to_message_id = body.get('reply_to_message_id')
    action = body.get('action', 'send')
    if not to or not subject:
        raise HTTPException(400, 'Destinataire et sujet requis')
    db = get_sync_db()
    if action == 'draft':
        try:
            if draft_id:
                db.execute(
                    'UPDATE drafts SET to_email=?, cc=?, subject=?, body_text=?, reply_to_message_id=?, updated_at=datetime(\'now\',\'localtime\') WHERE id=? AND user_id=?',
                    (to, cc, subject, text, reply_to_message_id, draft_id, user['id']))
            else:
                db.execute(
                    'INSERT INTO drafts (user_id, to_email, cc, subject, body_text, reply_to_message_id) VALUES (?,?,?,?,?,?)',
                    (user['id'], to, cc, subject, text, reply_to_message_id))
            db.commit()
            return {'ok': True, 'action': 'draft'}
        finally:
            db.close()
    result = send_email(to, subject, text, cc=cc, reply_to_message_id=reply_to_message_id)
    if result['ok']:
        try:
            message_id = result['message_id'].strip('<>')
            db.execute(
                'INSERT INTO sent_emails (id, user_id, to_email, cc, subject, body_text, reply_to_message_id) VALUES (?,?,?,?,?,?,?)',
                (message_id, user['id'], to, cc, subject, text, reply_to_message_id))
            if draft_id:
                db.execute('DELETE FROM drafts WHERE id=? AND user_id=?', (draft_id, user['id']))
            db.commit()
            return {'ok': True, 'action': 'sent', 'message_id': message_id}
        finally:
            db.close()
    db.close()
    raise HTTPException(500, f"Erreur d'envoi: {result['error']}")


# --- Brouillons ------------------------------------------------------------
@router.get('/drafts/list')
async def drafts_list_json(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        drafts = db.execute(
            'SELECT * FROM drafts WHERE user_id = ? ORDER BY updated_at DESC',
            (user['id'],)
        ).fetchall()
        return {'drafts': [dict(d) for d in drafts]}
    finally:
        db.close()

@router.delete('/drafts/{draft_id}')
async def delete_draft_json(request: Request, draft_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        db.execute('DELETE FROM drafts WHERE id=? AND user_id=?', (draft_id, user['id']))
        db.commit()
        return {'ok': True}
    finally:
        db.close()


# --- Envoyés ---------------------------------------------------------------
@router.get('/sent/list')
async def sent_list_json(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        sent = db.execute(
            'SELECT * FROM sent_emails WHERE user_id = ? ORDER BY sent_at DESC LIMIT 100',
            (user['id'],)
        ).fetchall()
        return {'sent': [dict(s) for s in sent]}
    finally:
        db.close()


# --- Lier email ↔ projet ---------------------------------------------------
@router.post('/{email_id}/link-project')
async def link_email_project(request: Request, email_id: str):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    body = await request.json()
    project_code = body.get('project_code', '').strip()

    # Try mailstore
    if _mailstore_available():
        from mailstore.query import link_to_project
        link_to_project(email_id, project_code)
        return {'ok': True}

    # Fallback: old DB
    db = get_sync_db()
    try:
        db.execute('UPDATE emails SET project_code = ? WHERE id = ?', (project_code, email_id))
        db.commit()
        return {'ok': True}
    finally:
        db.close()


# --- Créer tâche depuis email -----------------------------------------------
@router.post('/{email_id}/create-task')
async def create_task_from_email(request: Request, email_id: str):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    body = await request.json()
    title = body.get('title', '').strip()
    project_code = body.get('project_code', '').strip()
    if not title or not project_code:
        raise HTTPException(400, 'Titre et projet requis')
    db = get_sync_db()
    from database import get_next_task_code
    code = get_next_task_code(db)
    try:
        db.execute(
            'INSERT INTO tasks (code, title, description, project_code, created_by) VALUES (?, ?, ?, ?, ?)',
            (code, title, body.get('description', ''), project_code, user['id']))
        task_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        db.execute('INSERT OR IGNORE INTO email_tasks (email_id, task_id) VALUES (?, ?)', (email_id, task_id))
        db.commit()
        return {'ok': True, 'task_id': task_id, 'code': code}
    finally:
        db.close()


# --- Recherche full-text (mailstore FTS5) ----------------------------------
@router.get('/search/query')
async def search_emails(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    q = request.query_params.get('q', '').strip()
    if not q or len(q) < 3:
        return {'emails': []}

    if _mailstore_available():
        from mailstore.query import list_emails as ms_list
        rows = ms_list(search=q, limit=50)
        return {'emails': [_row_to_dict_email(r, 'mailstore') for r in rows]}

    # Fallback: LIKE search on old DB
    db = get_sync_db()
    try:
        rows = db.execute(
            'SELECT e.*, p.name as project_name FROM emails e '
            'LEFT JOIN projects p ON e.project_code = p.code '
            'WHERE e.subject LIKE ? OR e.sender LIKE ? OR e.body_text LIKE ? '
            'ORDER BY e.date_time DESC LIMIT 50',
            (f'%{q}%', f'%{q}%', f'%{q}%')
        ).fetchall()
        return {'emails': [_row_to_dict_email(r, 'legacy') for r in rows]}
    finally:
        db.close()


# --- Archive / Désarchiver ---------------------------------------------------
@router.post('/{email_id}/archive')
async def archive_email(request: Request, email_id: str):
    """Toggle archive status: adds/removes 'archived' label."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    if _mailstore_available():
        from mailstore import get_connection as ms_conn
        conn = ms_conn()
        row = conn.execute("SELECT labels FROM emails WHERE hash = ?", (email_id,)).fetchone()
        if not row:
            raise HTTPException(404)
        labels = (row['labels'] or '').split('\n')
        if 'archived' in labels:
            labels.remove('archived')
            archived = False
        else:
            labels.append('archived')
            archived = True
        conn.execute("UPDATE emails SET labels = ? WHERE hash = ?",
                     ('\n'.join(filter(None, labels)), email_id))
        conn.commit()
        return {'ok': True, 'archived': archived}
    raise HTTPException(404)


# --- Supprimer ---------------------------------------------------------------
@router.delete('/{email_id}')
async def delete_email(request: Request, email_id: str):
    """Soft-delete: adds 'trash' label."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    if _mailstore_available():
        from mailstore import get_connection as ms_conn
        conn = ms_conn()
        conn.execute("UPDATE emails SET labels = labels || '\ntrash' WHERE hash = ? AND labels NOT LIKE '%trash%'",
                     (email_id,))
        conn.commit()
        return {'ok': True}

    db = get_sync_db()
    try:
        db.execute('DELETE FROM emails WHERE id = ?', (email_id,))
        db.commit()
        return {'ok': True}
    finally:
        db.close()


# --- Télécharger toutes les pièces jointes en ZIP -----------------------------
@router.get('/{email_id}/attachments/zip')
async def download_all_attachments_zip(request: Request, email_id: str):
    """Return a ZIP archive of all attachments for an email."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    import email as em
    import zipfile
    import io
    from pathlib import Path
    from mailstore import BASE_DIR as MS_BASE
    from mailstore.query import get_email as ms_get

    email_data = ms_get(email_id)
    if not email_data:
        raise HTTPException(404)

    stored_path = email_data.get('stored_path', '')
    eml_path = Path(MS_BASE).parent / stored_path
    if not eml_path.exists():
        raise HTTPException(404)

    msg = em.message_from_bytes(eml_path.read_bytes(), policy=em.policy.default)

    buf = io.BytesIO()
    names_seen = set()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        count = 0
        for part in msg.iter_attachments():
            fn = part.get_filename()
            if not fn:
                continue
            # Avoid duplicate filenames
            if '.' in fn:
                base, ext = fn.rsplit('.', 1)
            else:
                base, ext = fn, ''
            unique_fn = fn
            n = 1
            while unique_fn in names_seen:
                unique_fn = f"{base}_{n}.{ext}" if ext else f"{base}_{n}"
                n += 1
            names_seen.add(unique_fn)

            content = part.get_content()
            if isinstance(content, str):
                content = content.encode('utf-8', errors='replace')
            zf.writestr(unique_fn, content)
            count += 1

        if count == 0:
            raise HTTPException(404, "No attachments")

    buf.seek(0)
    return Response(content=buf.getvalue(),
                    media_type='application/zip',
                    headers={'Content-Disposition': f'attachment; filename="attachments-{email_id[:8]}.zip"'})


# --- Télécharger pièce jointe ------------------------------------------------
@router.get('/{email_id}/attachment/{filename:path}')
async def download_attachment(request: Request, email_id: str, filename: str):
    """Serve an attachment file by filename within an email."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    import email as em
    from pathlib import Path
    from mailstore import BASE_DIR as MS_BASE
    from mailstore.query import get_email as ms_get

    email_data = ms_get(email_id)
    if not email_data:
        raise HTTPException(404)

    stored_path = email_data.get('stored_path', '')
    eml_path = Path(MS_BASE).parent / stored_path
    if not eml_path.exists():
        raise HTTPException(404)

    msg = em.message_from_bytes(eml_path.read_bytes(), policy=em.policy.default)
    for part in msg.iter_attachments():
        fn = part.get_filename()
        if fn and fn == filename:
            content = part.get_content()
            if isinstance(content, str):
                content = content.encode('utf-8', errors='replace')
            ct = part.get_content_type()
            return Response(content=content, media_type=ct,
                          headers={'Content-Disposition': f'attachment; filename="{fn}"'})
    raise HTTPException(404, f"Attachment not found: {filename}")
