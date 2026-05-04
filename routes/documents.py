"""MailApp V3 — Routes Documents"""
import os
import uuid
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from routes.auth import get_current_user
from database import get_sync_db
from config import DATA_DIR

router = APIRouter(prefix='/api/documents', tags=['documents'])
templates = Jinja2Templates(directory='templates')

UPLOAD_DIR = os.path.join(DATA_DIR, 'documents')

def get_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR

# ─── Download file (non-API path) ───────────────────────────────────────────
@router.get('/file/{doc_id}', include_in_schema=False)
async def serve_document(request: Request, doc_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login', 302)

    db = get_sync_db()
    try:
        doc = db.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
        if not doc:
            raise HTTPException(404, 'Document non trouve')

        # Check permissions
        if user['role'] != 'admin' and doc['project_code']:
            member = db.execute(
                'SELECT 1 FROM project_members WHERE project_code = ? AND user_id = ?',
                (doc['project_code'], user['id'])
            ).fetchone()
            if not member:
                raise HTTPException(403, 'Acces refuse')

        path = doc['stored_path']
        if not os.path.exists(path):
            raise HTTPException(404, 'Fichier non trouve')

        return FileResponse(path, filename=doc['filename'], media_type=doc['mime_type'] or 'application/octet-stream')
    finally:
        db.close()

# ─── API ─────────────────────────────────────────────────────────────────────
@router.post('/upload')
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    project_code: str = Form(''),
    task_id: str = Form(''),
    description: str = Form('')
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login', 302)

    # Sanitize filename
    safe_name = file.filename.replace('..', '').replace('/', '_').replace('\\', '_')
    ext = os.path.splitext(safe_name)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(get_upload_dir(), stored_name)

    content = await file.read()
    with open(stored_path, 'wb') as f:
        f.write(content)

    db = get_sync_db()
    try:
        cursor = db.execute(
            'INSERT INTO documents (filename, stored_path, size, mime_type, author_id, project_code, task_id, description) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (safe_name, stored_path, len(content), file.content_type or 'application/octet-stream',
             user['id'], project_code or None, task_id or None, description)
        )
        doc_id = cursor.lastrowid

        # Lier au projet
        if project_code:
            db.execute('INSERT OR IGNORE INTO project_documents (project_code, document_id) VALUES (?, ?)',
                      (project_code, doc_id))

        # Lier a la tache
        if task_id:
            db.execute('INSERT OR IGNORE INTO task_documents (task_id, document_id) VALUES (?, ?)',
                      (int(task_id), doc_id))

        # Premiere version
        db.execute(
            'INSERT INTO document_versions (document_id, version, stored_path, size, uploaded_by) VALUES (?, 1, ?, ?, ?)',
            (doc_id, stored_path, len(content), user['id'])
        )

        db.commit()

        if task_id:
            return RedirectResponse(f'/{project_code}/tasks?focus={task_id}&ok=doc_uploaded', 302)
        return RedirectResponse(f'/{project_code}/documents?ok=1', 302)
    finally:
        db.close()

@router.post('/{doc_id}/new-version')
async def new_version(
    request: Request,
    doc_id: int,
    file: UploadFile = File(...),
    comment: str = Form('')
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login', 302)

    db = get_sync_db()
    try:
        doc = db.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
        if not doc:
            raise HTTPException(404, 'Document non trouve')

        safe_name = file.filename.replace('..', '').replace('/', '_').replace('\\', '_')
        ext = os.path.splitext(safe_name)[1]
        stored_name = f"{uuid.uuid4().hex}{ext}"
        stored_path = os.path.join(get_upload_dir(), stored_name)

        content = await file.read()
        with open(stored_path, 'wb') as f:
            f.write(content)

        new_ver = doc['version'] + 1
        db.execute(
            'UPDATE documents SET version = ?, stored_path = ?, size = ?, filename = ?, '
            'updated_at = datetime("now","localtime") WHERE id = ?',
            (new_ver, stored_path, len(content), safe_name, doc_id)
        )
        db.execute(
            'INSERT INTO document_versions (document_id, version, stored_path, size, uploaded_by, comment) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (doc_id, new_ver, stored_path, len(content), user['id'], comment)
        )
        db.commit()
        return RedirectResponse(f'/{doc["project_code"]}/documents?ok=2', 302)
    finally:
        db.close()

@router.post('/{doc_id}/delete')
async def delete_document(request: Request, doc_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login', 302)

    db = get_sync_db()
    try:
        doc = db.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
        if not doc:
            raise HTTPException(404, 'Document non trouve')

        project = doc['project_code']
        db.execute('DELETE FROM document_versions WHERE document_id = ?', (doc_id,))
        db.execute('DELETE FROM project_documents WHERE document_id = ?', (doc_id,))
        db.execute('DELETE FROM task_documents WHERE document_id = ?', (doc_id,))
        db.execute('DELETE FROM comments WHERE entity_type="document" AND entity_id = ?', (doc_id,))
        db.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        db.commit()
        return RedirectResponse(f'/{project}/documents?ok=3', 302)
    finally:
        db.close()

@router.get('/{doc_id}/versions')
async def document_versions(request: Request, doc_id: int):
    user = get_current_user(request)
    if not user:
        return {'error': 'Non authentifie'}

    db = get_sync_db()
    try:
        doc = db.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
        if not doc:
            raise HTTPException(404, 'Document non trouve')

        versions = db.execute(
            'SELECT dv.*, u.username, u.display_name '
            'FROM document_versions dv LEFT JOIN users u ON dv.uploaded_by = u.id '
            'WHERE dv.document_id = ? ORDER BY dv.version DESC',
            (doc_id,)
        ).fetchall()

        return {
            'document': dict(doc),
            'versions': [dict(v) for v in versions]
        }
    finally:
        db.close()
