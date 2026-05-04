#!/usr/bin/env python3
"""MailApp V3 — Sync Gmail bidirectionnelle (sent folder + labels)
Synchronise les emails envoyés depuis MailApp dans la DB locale.
Utilise gog CLI (Gmail API) pour récupérer les emails du dossier Sent.
"""
import subprocess, json, sqlite3, os, sys
from datetime import datetime

DB_PATH = os.path.expanduser('~/.openclaw/workspace/mailapp-v3/data/mailapp.db')
GOG = os.path.expanduser('~/.npm-global/bin/gog')

def run_gog(*args):
    """Run gog CLI command and return JSON output"""
    try:
        result = subprocess.run(
            [GOG] + list(args),
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"  gog error: {result.stderr[:200]}")
            return None
        return json.loads(result.stdout) if result.stdout.strip() else None
    except Exception as e:
        print(f"  gog exception: {e}")
        return None

def sync_sent_folder():
    """Sync emails from Gmail Sent folder"""
    if not os.path.exists(GOG):
        print("⚠️ gog CLI non trouvé, skip sync sent")
        return

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Récupérer les derniers emails envoyés (50 max)
    emails = run_gog('gmail', 'list', '--label', 'SENT', '--max', '50', '--format', 'json')
    if not emails or not isinstance(emails, list):
        print("⚠️ Pas d'emails sent récupérés")
        db.close()
        return

    imported = 0
    for email in emails:
        eid = email.get('id', '')
        if not eid:
            continue

        # Vérifier si déjà présent
        existing = db.execute('SELECT id FROM emails WHERE id = ?', (eid,)).fetchone()
        if existing:
            continue

        # Récupérer le contenu complet
        detail = run_gog('gmail', 'get', eid, '--format', 'full')
        if not detail:
            continue

        try:
            db.execute(
                'INSERT OR IGNORE INTO emails (id, subject, sender, date_time, body_text, body_html, has_attachments) '
                'VALUES (?,?,?,?,?,?,?)',
                (
                    eid,
                    detail.get('subject', ''),
                    detail.get('from', ''),
                    detail.get('date', ''),
                    detail.get('snippet', '') or '',
                    '',
                    0
                )
            )
            imported += 1
        except Exception as e:
            print(f"  ⚠️ Erreur import sent {eid[:20]}: {e}")

    db.commit()
    db.close()
    print(f"✅ Sent sync: {imported} emails importés")

def sync_labels():
    """Sync email labels (read/unread, starred, etc.)"""
    if not os.path.exists(GOG):
        return

    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Récupérer les emails avec labels modifiés récemment
    emails = run_gog('gmail', 'list', '--max', '100', '--format', 'json')
    if not emails or not isinstance(emails, list):
        db.close()
        return

    updated = 0
    for email in emails:
        eid = email.get('id', '')
        labels = email.get('labelIds', [])
        if not eid:
            continue

        is_read = 'UNREAD' not in labels
        is_starred = 'STARRED' in labels

        try:
            db.execute(
                'UPDATE emails SET is_read = ?, is_starred = ? WHERE id = ?',
                (is_read, is_starred, eid)
            )
            if db.total_changes > 0:
                updated += 1
        except:
            pass

    db.commit()
    db.close()
    print(f"✅ Labels sync: {updated} emails mis à jour")

if __name__ == '__main__':
    print(f"📧 Gmail Bidirectional Sync — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    sync_sent_folder()
    sync_labels()
    print("✅ Sync terminée")
