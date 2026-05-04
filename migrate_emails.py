#!/usr/bin/env python3
"""Migration des emails depuis MailBox V1 vers MailApp V3"""
import sqlite3, os

V1_SRC = os.path.expanduser('~/.openclaw/workspace/mailbox/sqlite/truc.nguyen_at_scingenierie.fr/emails.db')
V3_DB = os.path.expanduser('~/.openclaw/workspace/mailapp-v3/data/mailapp.db')

src = sqlite3.connect(V1_SRC)
dst = sqlite3.connect(V3_DB)
src.row_factory = sqlite3.Row

emails = src.execute('SELECT * FROM emails ORDER BY date_time DESC').fetchall()
print(f"📧 {len(emails)} emails trouvés")

migrated = skipped = 0
for e in emails:
    eid = e['id']
    existing = dst.execute('SELECT id FROM emails WHERE id=?', (eid,)).fetchone()
    if existing:
        skipped += 1
        continue

    # Séparer HTML du texte depuis raw_content
    raw = e['raw_content'] if e['raw_content'] else ''
    body_text = ''
    body_html = ''
    if raw.startswith('text:'):
        body_text = raw[5:]
    elif raw.startswith('html:'):
        body_html = raw[5:]
    elif '<html' in raw.lower() or '<div' in raw.lower():
        body_html = raw
    else:
        body_text = raw

    subject = e['subject'] or ''
    sender = e['sender'] or ''
    date_time = e['date_time'] or ''
    has_att = 1 if (e['attachments'] or '') else 0
    proj = e['project'] if e['project'] else None

    try:
        dst.execute(
            'INSERT INTO emails (id, subject, sender, date_time, body_text, body_html, has_attachments, project_code) '
            'VALUES (?,?,?,?,?,?,?,?)',
            (eid, subject, sender, date_time, body_text, body_html, has_att, proj)
        )
        migrated += 1
    except Exception as ex:
        print(f"  ⚠️ Erreur {eid[:40]}: {ex}")
        skipped += 1

dst.commit()
src.close()
dst.close()
print(f"✅ Migration: {migrated} importés, {skipped} ignorés ({len(emails)} total)")
