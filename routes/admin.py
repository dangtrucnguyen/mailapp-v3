"""MailApp V3 — Routes Admin (API JSON)"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from routes.auth import get_current_user
from database import get_sync_db
from security import hash_password
import secrets

router = APIRouter(prefix='/api/admin', tags=['admin'])
templates = Jinja2Templates(directory='templates')


def admin_only(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(401)
    if user['role'] != 'admin':
        raise HTTPException(403, 'Admin requis')
    return user


@router.get('/users')
async def users_list(request: Request):
    admin_only(request)
    db = get_sync_db()
    try:
        users = db.execute('SELECT * FROM users ORDER BY username').fetchall()
        return {'users': [dict(u) for u in users]}
    finally:
        db.close()


@router.get('/invitations')
async def invitations_list(request: Request):
    admin_only(request)
    db = get_sync_db()
    try:
        invs = db.execute(
            "SELECT * FROM invitations ORDER BY created_at DESC"
        ).fetchall()
        return {'invitations': [dict(i) for i in invs]}
    finally:
        db.close()


@router.post('/users/invite')
async def invite_user(request: Request):
    admin_only(request)
    body = await request.json()
    email = body.get('email', '').strip()
    role = body.get('role', 'utilisateur')
    if not email:
        raise HTTPException(400, 'Email requis')
    if role not in ('admin', 'manager', 'utilisateur'):
        raise HTTPException(400, 'Rôle invalide')
    db = get_sync_db()
    try:
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            raise HTTPException(400, 'Cet email est déjà enregistré')
        existing_inv = db.execute(
            "SELECT id FROM invitations WHERE email = ? AND accepted_at IS NULL AND expires_at > datetime('now','localtime')",
            (email,)
        ).fetchone()
        if existing_inv:
            raise HTTPException(400, 'Une invitation est déjà en cours pour cet email')
        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO invitations (email, role, token, expires_at, created_by) VALUES (?, ?, ?, datetime('now', '+7 days'), ?)",
            (email, role, token, 1))
        db.commit()
        return {'ok': True, 'token': token}
    finally:
        db.close()


@router.post('/users/invite/resend')
async def resend_invitation(request: Request):
    admin_only(request)
    body = await request.json()
    inv_id = body.get('invitation_id')
    if not inv_id:
        raise HTTPException(400)
    db = get_sync_db()
    try:
        inv = db.execute('SELECT * FROM invitations WHERE id = ?', (inv_id,)).fetchone()
        if not inv:
            raise HTTPException(404)
        new_token = secrets.token_urlsafe(32)
        db.execute(
            "UPDATE invitations SET token = ?, expires_at = datetime('now', '+7 days'), created_at = datetime('now','localtime') WHERE id = ?",
            (new_token, inv_id))
        db.commit()
        return {'ok': True, 'token': new_token}
    finally:
        db.close()


@router.post('/users/{user_id}/toggle')
async def toggle_user(request: Request, user_id: int):
    admin_only(request)
    db = get_sync_db()
    try:
        user = db.execute('SELECT is_active FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            raise HTTPException(404)
        new_state = 0 if user['is_active'] else 1
        db.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_state, user_id))
        db.commit()
        return {'ok': True, 'is_active': bool(new_state)}
    finally:
        db.close()


@router.post('/users/{user_id}/role')
async def update_user_role(request: Request, user_id: int):
    admin_only(request)
    body = await request.json()
    role = body.get('role')
    if role not in ('admin', 'manager', 'utilisateur'):
        raise HTTPException(400, 'Rôle invalide')
    db = get_sync_db()
    try:
        db.execute('UPDATE users SET role = ? WHERE id = ?', (role, user_id))
        db.commit()
        return {'ok': True}
    finally:
        db.close()
