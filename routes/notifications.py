"""MailApp V3 Phase 5 — Routes Notifications (Push, Webhooks, SSE)"""
import json
import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from routes.auth import get_current_user
from database import get_sync_db

router = APIRouter(prefix='/api/notifications', tags=['notifications'])
templates = Jinja2Templates(directory='templates')

# ─── Push subscription ───────────────────────────────────────────────────────
@router.post('/push/subscribe')
async def push_subscribe(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    body = await request.json()
    subscription = body.get('subscription')
    if not subscription:
        raise HTTPException(400, 'Subscription required')

    db = get_sync_db()
    try:
        # Deduplicate by endpoint
        endpoint = subscription.get('endpoint', '')
        existing = db.execute(
            'SELECT id FROM push_subscriptions WHERE endpoint = ? AND user_id = ?',
            (endpoint, user['id'])
        ).fetchone()

        sub_json = json.dumps(subscription)
        if existing:
            db.execute(
                'UPDATE push_subscriptions SET subscription_json = ?, updated_at = datetime(\'now\',\'localtime\') WHERE id = ?',
                (sub_json, existing['id'])
            )
        else:
            db.execute(
                'INSERT INTO push_subscriptions (user_id, endpoint, subscription_json) VALUES (?,?,?)',
                (user['id'], endpoint, sub_json)
            )
        db.commit()
        return {'ok': True}
    finally:
        db.close()


@router.post('/push/unsubscribe')
async def push_unsubscribe(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    body = await request.json()
    endpoint = body.get('endpoint', '')

    db = get_sync_db()
    try:
        db.execute('DELETE FROM push_subscriptions WHERE endpoint = ? AND user_id = ?',
                   (endpoint, user['id']))
        db.commit()
        return {'ok': True}
    finally:
        db.close()


@router.get('/push/vapid-public-key')
async def vapid_public_key(request: Request):
    from services.push import get_vapid_keys
    keys = get_vapid_keys()
    return {'public_key': keys['public_key']}


# ─── Webhooks CRUD ───────────────────────────────────────────────────────────
@router.get('/webhooks')
async def list_webhooks(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login', 302)

    db = get_sync_db()
    try:
        if user['role'] == 'admin':
            hooks = db.execute('SELECT * FROM webhooks ORDER BY created_at DESC').fetchall()
        else:
            # Users see webhooks for their projects
            hooks = db.execute(
                'SELECT w.* FROM webhooks w JOIN project_members pm ON w.project_code = pm.project_code '
                'WHERE pm.user_id = ? ORDER BY w.created_at DESC',
                (user['id'],)
            ).fetchall()

        projects = db.execute('SELECT code, name FROM projects ORDER BY name').fetchall()
        return templates.TemplateResponse('webhooks.html', {
            'request': request, 'user': user,
            'webhooks': [dict(h) for h in hooks],
            'projects': [dict(p) for p in projects]
        })
    finally:
        db.close()


@router.post('/webhooks/api/create')
async def create_webhook(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login', 302)

    form = await request.form()
    url = form.get('url', '').strip()
    project_code = form.get('project_code', '').strip() or None
    events = form.get('events', 'task.created,task.updated').strip()

    if not url:
        raise HTTPException(400, 'URL requise')

    import secrets
    secret = secrets.token_hex(16)

    db = get_sync_db()
    try:
        db.execute(
            'INSERT INTO webhooks (url, project_code, events, secret, created_by) VALUES (?,?,?,?,?)',
            (url, project_code, events, secret, user['id'])
        )
        db.commit()
        return RedirectResponse('/notifications/webhooks?ok=1', 302)
    finally:
        db.close()


@router.post('/webhooks/api/{hook_id}/delete')
async def delete_webhook(request: Request, hook_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login', 302)

    db = get_sync_db()
    try:
        db.execute('DELETE FROM webhooks WHERE id = ? AND (created_by = ? OR ? = \'admin\')',
                   (hook_id, user['id'], user['role']))
        db.commit()
        return RedirectResponse('/notifications/webhooks?ok=2', 302)
    finally:
        db.close()


# ─── SSE (Server-Sent Events) pour live updates ──────────────────────────────
@router.get('/stream')
async def sse_stream(request: Request):
    """Stream d'événements en temps réel via SSE"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)

    async def event_generator():
        db = get_sync_db()
        last_check = None
        try:
            while True:
                # Vérifier les nouvelles tâches
                if last_check:
                    new_tasks = db.execute(
                        'SELECT COUNT(*) as cnt FROM tasks WHERE created_at > ?',
                        (last_check,)
                    ).fetchone()
                    if new_tasks and new_tasks['cnt'] > 0:
                        yield f'data: {{"event":"tasks.updated","count":{new_tasks["cnt"]}}}\n\n'
                last_check = asyncio.get_event_loop().time()

                # Petite pause pour éviter le polling CPU intensif
                await asyncio.sleep(10)
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )
