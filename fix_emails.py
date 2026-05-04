#!/usr/bin/env python3
"""Fix email body_text/body_html in mailapp-v3 database.
Re-parses raw email content and extracts proper text+HTML body."""
import sqlite3
from email import policy
from email.parser import BytesParser

DEST_DB = '/home/sci/.openclaw/workspace/mailapp-v3/data/mailapp.db'
ARCHIVE_DB = '/home/sci/.openclaw/workspace/mailview-archive/emails.db'

def extract_body(raw_bytes):
    """Parse raw email and return clean body_text and body_html"""
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    except:
        return '', ''

    body_text = ''
    body_html = ''

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain' and not body_text:
                try:
                    payload = part.get_content()
                    body_text = payload if isinstance(payload, str) else payload.decode(errors='replace')
                except:
                    body_text = str(part.get_payload(decode=True) or b'', errors='replace')
            elif ct == 'text/html' and not body_html:
                try:
                    payload = part.get_content()
                    body_html = payload if isinstance(payload, str) else payload.decode(errors='replace')
                except:
                    body_html = str(part.get_payload(decode=True) or b'', errors='replace')
    else:
        ct = msg.get_content_type()
        try:
            payload = msg.get_content()
            content = payload if isinstance(payload, str) else payload.decode(errors='replace')
        except:
            content = str(msg.get_payload(decode=True) or b'', errors='replace')

        if ct == 'text/html':
            body_html = content
        else:
            body_text = content

    return body_text.strip(), body_html.strip()


def fix_from_archive():
    """Re-import from archive with proper body parsing"""
    dest = sqlite3.connect(DEST_DB)
    src = sqlite3.connect(ARCHIVE_DB)
    src.row_factory = sqlite3.Row
    dest.row_factory = sqlite3.Row

    # Get all emails from archive
    all_emails = src.execute('SELECT * FROM emails ORDER BY date_ts DESC').fetchall()
    fixed = 0

    for email in all_emails:
        eid = email['id']
        # Check if this email exists in dest
        existing = dest.execute('SELECT * FROM emails WHERE id = ?', (eid,)).fetchone()
        if not existing:
            continue

        src_text = email['body_text'] or ''
        src_html = email['body_html'] or ''
        src_subject = email['subject'] or ''
        src_sender = email['sender'] or ''
        src_date = email['date_time'] or ''
        src_recipients = email['recipients'] or ''

        # If source has proper body data, use it
        if src_html or (src_text and not src_text.startswith('Delivered-To')):
            dest.execute(
                'UPDATE emails SET subject=?, sender=?, date_time=?, recipients=?, body_text=?, body_html=? WHERE id=?',
                (src_subject, src_sender, src_date, src_recipients, src_text, src_html, eid)
            )
            fixed += 1

    dest.commit()
    dest.close()
    src.close()
    print(f'✅ Fixed {fixed} emails from archive')

if __name__ == '__main__':
    fix_from_archive()
