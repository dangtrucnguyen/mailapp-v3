"""MailApp V3 Phase 5 — Service Webhooks"""
import json
import time
import urllib.request

def dispatch_webhook(event_type: str, payload: dict, db=None):
    """Dispatch event to all matching webhooks.
    event_type: 'task.created', 'task.updated', 'email.received', 'document.uploaded', etc.
    payload: dict with event data (project_code, data, user, etc.)
    """
    if db is None:
        from database import get_sync_db
        db = get_sync_db()
        own_db = True
    else:
        own_db = False

    try:
        project_code = payload.get('project_code', '')
        hooks = db.execute(
            'SELECT * FROM webhooks WHERE is_active = 1 AND (project_code = ? OR project_code IS NULL)',
            (project_code,)
        ).fetchall()

        for hook in hooks:
            events = json.loads(hook['events'] or '[]')
            if event_type not in events and '*' not in events:
                continue

            try:
                req = urllib.request.Request(
                    hook['url'],
                    data=json.dumps({
                        'event': event_type,
                        'timestamp': int(time.time()),
                        'payload': payload
                    }).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'X-Webhook-Secret': hook['secret'] or '',
                        'X-MailApp-Event': event_type
                    },
                    method='POST'
                )
                resp = urllib.request.urlopen(req, timeout=5)
                # Log delivery
                db.execute(
                    'INSERT INTO webhook_logs (webhook_id, event_type, status_code, response_body) VALUES (?,?,?,?)',
                    (hook['id'], event_type, resp.status, resp.read().decode()[:500])
                )
                db.commit()
            except Exception as e:
                db.execute(
                    'INSERT INTO webhook_logs (webhook_id, event_type, status_code, response_body) VALUES (?,?,?,?)',
                    (hook['id'], event_type, -1, str(e)[:500])
                )
                db.commit()
    finally:
        if own_db:
            db.close()
