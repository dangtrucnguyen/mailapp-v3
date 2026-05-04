"""MailApp V3 — Routes d'authentification"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import uuid
import sqlite3

from security import hash_password, verify_password, create_access_token, decode_access_token
from models import UserCreate, UserLogin, InvitationCreate, InvitationAccept, TokenResponse
from database import get_sync_db

router = APIRouter(tags=['auth'])
templates = Jinja2Templates(directory='templates')

# ─── Dépendance : utilisateur courant depuis cookie JWT ──────────────────────
def get_current_user(request: Request):
    token = request.cookies.get('mailapp_token')
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get('sub')
    if not user_id:
        return None
    db = get_sync_db()
    try:
        user = db.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,)).fetchone()
        return dict(user) if user else None
    finally:
        db.close()

async def get_current_user_api(request: Request):
    """Version pour API (ne redirige pas, renvoie None)"""
    token = request.cookies.get('mailapp_token')
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    import aiosqlite
    from database import get_db
    db = await get_db()
    try:
        user = await db.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (payload['sub'],))
        row = await user.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()

# ─── Pages ───────────────────────────────────────────────────────────────────
@router.get('/login')
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse('/dashboard', 302)
    return templates.TemplateResponse('login.html', {
        'request': request, 'user': None
    })

@router.get('/register')
async def register_page(request: Request):
    return templates.TemplateResponse('register.html', {
        'request': request, 'user': None
    })

@router.get('/accept-invitation')
async def accept_invitation_page(request: Request, token: str = ''):
    db = get_sync_db()
    try:
        inv = db.execute(
            "SELECT * FROM invitations WHERE token = ? AND accepted_at IS NULL "
            "AND expires_at > datetime('now','localtime')", (token,)
        ).fetchone()
        if not inv:
            return templates.TemplateResponse('register.html', {
                'request': request, 'user': None,
                'error': 'Invitation invalide ou expiree.',
                'invitation_email': '', 'invitation_token': ''
            })
        return templates.TemplateResponse('register.html', {
            'request': request, 'user': None,
            'invitation_email': inv['email'],
            'invitation_token': token
        })
    finally:
        db.close()

# ─── API ─────────────────────────────────────────────────────────────────────
@router.post('/api/auth/login')
async def api_login(request: Request, form: UserLogin):
    db = get_sync_db()
    try:
        user = db.execute(
            'SELECT * FROM users WHERE username = ? AND is_active = 1',
            (form.username,)
        ).fetchone()
        if not user or not verify_password(form.password, user['password_hash']):
            raise HTTPException(401, 'Identifiants invalides')

        # Mise a jour last_login
        db.execute("UPDATE users SET last_login = datetime('now','localtime') WHERE id = ?", (user['id'],))
        db.commit()

        token = create_access_token({'sub': str(user['id']), 'role': user['role']})

        response = JSONResponse({
            'access_token': token,
            'token_type': 'bearer',
            'user': {k: user[k] for k in user.keys() if k != 'password_hash'}
        })
        response.set_cookie('mailapp_token', token, httponly=True, samesite='lax',
                           max_age=28800, secure=False)  # secure=True en prod
        return response
    finally:
        db.close()

@router.post('/api/auth/register')
async def api_register(request: Request, form: UserCreate):
    db = get_sync_db()
    try:
        existing = db.execute(
            'SELECT id FROM users WHERE username = ? OR email = ?',
            (form.username, form.email)
        ).fetchone()
        if existing:
            raise HTTPException(400, 'Utilisateur ou email deja existant')

        hashed = hash_password(form.password)
        cursor = db.execute(
            'INSERT INTO users (username, email, password_hash, display_name) VALUES (?, ?, ?, ?)',
            (form.username, form.email, hashed, form.display_name)
        )
        db.commit()
        user_id = cursor.lastrowid

        user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        token = create_access_token({'sub': str(user['id']), 'role': user['role']})

        response = JSONResponse({
            'access_token': token,
            'user': {k: user[k] for k in user.keys() if k != 'password_hash'}
        })
        response.set_cookie('mailapp_token', token, httponly=True, samesite='lax', max_age=28800)
        return response
    finally:
        db.close()

@router.post('/api/auth/register-with-invitation')
async def api_register_invitation(request: Request, form: InvitationAccept):
    db = get_sync_db()
    try:
        inv = db.execute(
            "SELECT * FROM invitations WHERE token = ? AND accepted_at IS NULL "
            "AND expires_at > datetime('now','localtime')", (form.token,)
        ).fetchone()
        if not inv:
            raise HTTPException(400, 'Invitation invalide ou expiree')

        # Check si l'utilisateur existe deja
        existing = db.execute('SELECT id FROM users WHERE username = ? OR email = ?',
                             (form.username, inv['email'])).fetchone()
        if existing:
            raise HTTPException(400, 'Utilisateur ou email deja existant')

        hashed = hash_password(form.password)
        cursor = db.execute(
            'INSERT INTO users (username, email, password_hash, display_name, role) VALUES (?, ?, ?, ?, ?)',
            (form.username, inv['email'], hashed, form.display_name, inv['role'])
        )

        # Marquer l'invitation comme acceptee
        db.execute("UPDATE invitations SET accepted_at = datetime('now','localtime') WHERE token = ?", (form.token,))
        db.commit()

        user_id = cursor.lastrowid
        user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        token = create_access_token({'sub': str(user['id']), 'role': user['role']})

        response = JSONResponse({
            'access_token': token,
            'user': {k: user[k] for k in user.keys() if k != 'password_hash'}
        })
        response.set_cookie('mailapp_token', token, httponly=True, samesite='lax', max_age=28800)
        return response
    finally:
        db.close()

@router.get('/api/auth/logout')
async def api_logout():
    response = RedirectResponse('/login', 302)
    response.delete_cookie('mailapp_token')
    return response

@router.get('/api/auth/me')
async def api_me(request: Request):
    user = await get_current_user_api(request)
    if not user:
        raise HTTPException(401, 'Non authentifie')
    return {'user': {k: user[k] for k in user.keys() if k != 'password_hash'}}
