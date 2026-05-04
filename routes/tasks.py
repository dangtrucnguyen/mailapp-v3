"""MailApp V3 — Routes Tâches (API JSON)"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from routes.auth import get_current_user
from database import get_sync_db, get_next_task_code

router = APIRouter(prefix='/api/tasks', tags=['tasks'])
templates = Jinja2Templates(directory='templates')


@router.get('')
@router.get('/')
async def tasks_list(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        if user['role'] == 'admin':
            tasks = db.execute(
                'SELECT t.*, p.name as project_name, u.display_name as assignee_name '
                'FROM tasks t LEFT JOIN projects p ON t.project_code = p.code '
                'LEFT JOIN users u ON t.assigned_to = u.id ORDER BY t.created_at DESC'
            ).fetchall()
        else:
            tasks = db.execute(
                'SELECT t.*, p.name as project_name, u.display_name as assignee_name '
                'FROM tasks t JOIN project_members pm ON t.project_code = pm.project_code '
                'LEFT JOIN projects p ON t.project_code = p.code '
                'LEFT JOIN users u ON t.assigned_to = u.id '
                'WHERE pm.user_id = ? ORDER BY t.created_at DESC', (user['id'],)
            ).fetchall()
        return {'tasks': [dict(t) for t in tasks]}
    finally:
        db.close()


@router.post('/create')
async def create_task(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    body = await request.json()
    title = body.get('title', '').strip()
    project_code = body.get('project_code', '').strip()
    if not title or not project_code:
        raise HTTPException(400, 'Titre et projet requis')
    db = get_sync_db()
    code = get_next_task_code(db)
    try:
        db.execute(
            'INSERT INTO tasks (code, title, description, status, priority, due_date, project_code, assigned_to, created_by) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (code, title, body.get('description', ''), body.get('status', 'A faire'),
             body.get('priority', 'Normale'), body.get('due_date') or None,
             project_code, body.get('assigned_to') or None, user['id']))
        task_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        email_id = body.get('email_id')
        if email_id:
            db.execute('INSERT OR IGNORE INTO email_tasks (email_id, task_id) VALUES (?, ?)', (email_id, task_id))
        db.commit()
        assigned_to = body.get('assigned_to')
        if assigned_to:
            try:
                from services.push import notify_user
                notify_user(int(assigned_to), 'Nouvelle tâche assignée', f'{code}: {title}', '/tasks', db)
            except: pass
        try:
            from services.webhooks import dispatch_webhook
            dispatch_webhook('task.created', {
                'project_code': project_code, 'task_id': task_id, 'code': code,
                'title': title, 'created_by': user['username']}, db)
        except: pass
        return {'ok': True, 'task_id': task_id, 'code': code}
    finally:
        db.close()


@router.put('/{task_id}')
async def update_task(request: Request, task_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    body = await request.json()
    db = get_sync_db()
    try:
        db.execute(
            'UPDATE tasks SET title=?, description=?, status=?, priority=?, due_date=?, assigned_to=?, updated_at=datetime("now","localtime") WHERE id=?',
            (body.get('title'), body.get('description'), body.get('status'),
             body.get('priority'), body.get('due_date') or None,
             body.get('assigned_to') or None, task_id))
        email_id = body.get('email_id')
        if email_id:
            db.execute('INSERT OR IGNORE INTO email_tasks (email_id, task_id) VALUES (?, ?)', (email_id, task_id))
        db.commit()
        return {'ok': True}
    finally:
        db.close()


@router.post('/{task_id}/status')
async def update_task_status(request: Request, task_id: int):
    import json
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    body = await request.body()
    data = json.loads(body)
    new_status = data.get('status')
    if new_status not in ('A faire', 'En cours', 'En révision', 'Terminé'):
        raise HTTPException(400, 'Statut invalide')
    db = get_sync_db()
    try:
        db.execute("UPDATE tasks SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
                  (new_status, task_id))
        db.commit()
        return {'ok': True, 'status': new_status}
    finally:
        db.close()


@router.delete('/{task_id}')
async def delete_task(request: Request, task_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        db.execute('DELETE FROM tasks WHERE id=?', (task_id,))
        db.execute('DELETE FROM comments WHERE entity_type="task" AND entity_id=?', (task_id,))
        db.execute('DELETE FROM task_documents WHERE task_id=?', (task_id,))
        db.execute('DELETE FROM email_tasks WHERE task_id=?', (task_id,))
        db.commit()
        return {'ok': True}
    finally:
        db.close()


@router.get('/{task_id}/links')
async def task_links(request: Request, task_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    db = get_sync_db()
    try:
        emails = db.execute(
            'SELECT e.id, e.subject, e.sender, e.date_time '
            'FROM emails e JOIN email_tasks et ON e.id = et.email_id WHERE et.task_id = ?', (task_id,)
        ).fetchall()
        docs = db.execute(
            'SELECT d.id, d.filename, d.version, d.status '
            'FROM documents d JOIN task_documents td ON d.id = td.document_id WHERE td.task_id = ?', (task_id,)
        ).fetchall()
        comments = db.execute(
            'SELECT c.*, u.username, u.display_name FROM comments c '
            'JOIN users u ON c.user_id = u.id '
            'WHERE c.entity_type="task" AND c.entity_id = ? ORDER BY c.created_at', (task_id,)
        ).fetchall()
        return {
            'emails': [dict(e) for e in emails],
            'documents': [dict(d) for d in docs],
            'comments': [dict(c) for c in comments]
        }
    finally:
        db.close()


@router.post('/{task_id}/comment')
async def add_comment(request: Request, task_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    body = await request.json()
    content = body.get('content', '').strip()
    if not content:
        raise HTTPException(400, 'Commentaire vide')
    db = get_sync_db()
    try:
        db.execute(
            'INSERT INTO comments (entity_type, entity_id, user_id, content) VALUES (?, ?, ?, ?)',
            ('task', task_id, user['id'], content))
        db.commit()
        return {'ok': True}
    finally:
        db.close()
