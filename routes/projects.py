"""MailApp V3 — Routes Projets + Membres (API JSON)"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from routes.auth import get_current_user
from database import get_sync_db

router = APIRouter(prefix='/api/projects', tags=['projects'])
templates = Jinja2Templates(directory='templates')


@router.get('')
@router.get('/')
async def projects_list(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        if user['role'] == 'admin':
            projects = db.execute('SELECT * FROM projects ORDER BY created_at DESC').fetchall()
        else:
            projects = db.execute(
                'SELECT p.* FROM projects p '
                'JOIN project_members pm ON p.code = pm.project_code '
                'WHERE pm.user_id = ? ORDER BY p.created_at DESC',
                (user['id'],)
            ).fetchall()
        projects = [dict(p) for p in projects]
        for p in projects:
            cnt = db.execute('SELECT COUNT(*) FROM project_members WHERE project_code = ?', (p['code'],)).fetchone()
            p['member_count'] = cnt[0]
        return {'projects': projects}
    finally:
        db.close()


@router.get('/{code}')
async def project_detail(request: Request, code: str):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        project = db.execute('SELECT * FROM projects WHERE code = ?', (code,)).fetchone()
        if not project:
            raise HTTPException(404)
        project = dict(project)
        if user['role'] != 'admin':
            member = db.execute(
                'SELECT * FROM project_members WHERE project_code = ? AND user_id = ?',
                (code, user['id'])
            ).fetchone()
            if not member:
                raise HTTPException(403)
        members = db.execute(
            'SELECT pm.*, u.username, u.email, u.display_name, u.avatar_url '
            'FROM project_members pm JOIN users u ON pm.user_id = u.id '
            'WHERE pm.project_code = ?', (code,)
        ).fetchall()
        project['members'] = [dict(m) for m in members]
        # Tasks count by status
        tasks = db.execute(
            'SELECT t.*, u.display_name as assignee_name FROM tasks t '
            'LEFT JOIN users u ON t.assigned_to = u.id '
            'WHERE t.project_code = ? ORDER BY t.status, t.priority', (code,)
        ).fetchall()
        project['tasks'] = [dict(t) for t in tasks]
        # Emails
        emails = db.execute(
            'SELECT * FROM emails WHERE project_code = ? ORDER BY date_time DESC LIMIT 100', (code,)
        ).fetchall()
        project['emails'] = [dict(e) for e in emails]
        # Documents
        docs = db.execute(
            'SELECT d.*, u.display_name as author_name FROM documents d '
            'LEFT JOIN users u ON d.author_id = u.id '
            'WHERE d.project_code = ? '
            'OR d.id IN (SELECT document_id FROM project_documents WHERE project_code = ?) '
            'ORDER BY d.created_at DESC', (code, code)
        ).fetchall()
        project['documents'] = [dict(d) for d in docs]
        return {'project': project}
    finally:
        db.close()


@router.post('/create')
async def create_project(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    body = await request.json()
    code = body.get('code', '').strip().upper()
    name = body.get('name', '').strip()
    description = body.get('description', '').strip()
    if not code or not name:
        raise HTTPException(400, 'Code et nom requis')
    db = get_sync_db()
    try:
        existing = db.execute('SELECT code FROM projects WHERE code = ?', (code,)).fetchone()
        if existing:
            raise HTTPException(400, 'Ce code projet existe déjà')
        db.execute(
            'INSERT INTO projects (code, name, description, created_by) VALUES (?, ?, ?, ?)',
            (code, name, description, user['id']))
        db.execute(
            'INSERT INTO project_members (project_code, user_id, role, can_manage_members, can_assign_tasks, can_validate_docs) '
            'VALUES (?, ?, "chef", 1, 1, 1)', (code, user['id']))
        db.commit()
        return {'ok': True, 'code': code}
    finally:
        db.close()


@router.post('/{code}/members/add')
async def add_member(request: Request, code: str):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        if user['role'] != 'admin':
            member = db.execute(
                'SELECT * FROM project_members WHERE project_code = ? AND user_id = ? AND can_manage_members = 1',
                (code, user['id'])).fetchone()
            if not member:
                raise HTTPException(403)
        body = await request.json()
        target_id = int(body.get('user_id', 0))
        role = body.get('role', 'lecteur')
        if role not in ('chef', 'collaborateur', 'lecteur'):
            raise HTTPException(400, 'Rôle invalide')
        existing = db.execute(
            'SELECT * FROM project_members WHERE project_code = ? AND user_id = ?', (code, target_id)).fetchone()
        if existing:
            raise HTTPException(400, 'Déjà membre')
        db.execute(
            'INSERT INTO project_members (project_code, user_id, role, invited_by) VALUES (?, ?, ?, ?)',
            (code, target_id, role, user['id']))
        db.commit()
        return {'ok': True}
    finally:
        db.close()


@router.post('/{code}/members/{member_id}/update')
async def update_member(request: Request, code: str, member_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        if user['role'] != 'admin':
            member = db.execute(
                'SELECT * FROM project_members WHERE project_code = ? AND user_id = ? AND can_manage_members = 1',
                (code, user['id'])).fetchone()
            if not member:
                raise HTTPException(403)
        body = await request.json()
        role = body.get('role')
        if role and role in ('chef', 'collaborateur', 'lecteur'):
            db.execute('UPDATE project_members SET role = ? WHERE project_code = ? AND user_id = ?',
                      (role, code, member_id))
        db.commit()
        return {'ok': True}
    finally:
        db.close()


@router.post('/{code}/members/{member_id}/remove')
async def remove_member(request: Request, code: str, member_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        if user['role'] != 'admin':
            member = db.execute(
                'SELECT * FROM project_members WHERE project_code = ? AND user_id = ? AND can_manage_members = 1',
                (code, user['id'])).fetchone()
            if not member:
                raise HTTPException(403)
        db.execute('DELETE FROM project_members WHERE project_code = ? AND user_id = ?', (code, member_id))
        db.commit()
        return {'ok': True}
    finally:
        db.close()
