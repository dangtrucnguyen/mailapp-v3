"""MailApp V3 — Application principale FastAPI"""
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from config import APP_NAME, APP_HOST, APP_PORT
from database import init_db
from routes import auth, admin, projects, tasks, documents, emails, notifications

templates = Jinja2Templates(directory='templates')

SPA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'dist')

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from database import get_db
    from security import hash_password
    db = await get_db()
    try:
        existing = await db.execute('SELECT COUNT(*) FROM users')
        count = (await existing.fetchone())[0]
        if count == 0:
            await db.execute(
                "INSERT INTO users (username, email, password_hash, display_name, role) "
                "VALUES (?, ?, ?, ?, 'admin')",
                ('admin', 'truc.nguyen@scingenierie.fr', hash_password('changeme123'), 'Truc Nguyen')
            )
            await db.commit()
            print("👤 Compte admin cree: admin / changeme123")
    finally:
        await db.close()
    yield

app = FastAPI(title=APP_NAME, lifespan=lifespan)

# CORS: allow Tauri desktop app (tauri://localhost origin) + web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://op13.scigroup.fr",
        "http://192.168.1.242:6000",
        "http://localhost:*",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets (Vue SPA + legacy)
app.mount('/assets', StaticFiles(directory=os.path.join(SPA_DIR, 'assets')), name='spa_assets')
app.mount('/css', StaticFiles(directory='static/css'), name='static_css')
app.mount('/fonts', StaticFiles(directory='static/fonts'), name='static_fonts')

# API Blueprints
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(emails.router)
app.include_router(notifications.router)

# ─── SPA service worker & manifest ───────────────────────────────────────────
@app.get('/sw.js')
async def service_worker():
    return FileResponse(os.path.join(SPA_DIR, 'sw.js'))

@app.get('/workbox-{rest:path}')
async def workbox_files(rest: str):
    return FileResponse(os.path.join(SPA_DIR, f'workbox-{rest}'))

@app.get('/registerSW.js')
async def register_sw():
    return FileResponse(os.path.join(SPA_DIR, 'registerSW.js'))

@app.get('/manifest.webmanifest')
async def manifest():
    return FileResponse(os.path.join(SPA_DIR, 'manifest.webmanifest'))

# ─── Document downloads (non-API) ────────────────────────────────────────────
@app.get('/documents/file/{doc_id}')
async def serve_document(doc_id: int, request: Request):
    from routes.auth import get_current_user
    user = get_current_user(request)
    if not user:
        return RedirectResponse('/login', 302)
    from database import get_sync_db
    import os
    db = get_sync_db()
    try:
        doc = db.execute('SELECT * FROM documents WHERE id = ?', (doc_id,)).fetchone()
        if not doc:
            raise HTTPException(status_code=404)
        if user['role'] != 'admin' and doc['project_code']:
            member = db.execute(
                'SELECT 1 FROM project_members WHERE project_code = ? AND user_id = ?',
                (doc['project_code'], user['id'])
            ).fetchone()
            if not member:
                raise HTTPException(status_code=403)
        path = doc['stored_path']
        if not os.path.exists(path):
            raise HTTPException(status_code=404)
        return FileResponse(path, filename=doc['filename'],
                          media_type=doc['mime_type'] or 'application/octet-stream')
    finally:
        db.close()

# ─── Redirect racine ─────────────────────────────────────────────────────────
@app.get('/')
async def root():
    index_path = os.path.join(SPA_DIR, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return RedirectResponse('/login', 302)

# ─── Pages de test (AVANT le catch-all SPA) ─────────────────────────────────
@app.get('/icon-test.html')
async def icon_test():
    return FileResponse(os.path.join(SPA_DIR, 'icon-test.html'))

@app.get('/font-test.html')
async def font_test():
    return FileResponse(os.path.join(SPA_DIR, 'font-test.html'))

# ─── SPA fallback (après toutes les routes API) ──────────────────────────────
@app.get('/{full_path:path}')
async def spa_fallback(request: Request, full_path: str):
    """Sert le SPA Vue.js pour toute route non-API"""
    # Ne pas servir les routes API (déjà traitées par les blueprints)
    if full_path.startswith('api/') or full_path.startswith('documents/'):
        return HTMLResponse('Not Found', status_code=404)
    # Servir index.html pour le routage SPA
    index_path = os.path.join(SPA_DIR, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse('SPA not built. Run: cd frontend && npm run build', status_code=500)

# ⚠️ La route @app.get('/') est définie avant le catch-all ci-dessus

# ─── Run ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host=APP_HOST, port=APP_PORT, reload=True)
