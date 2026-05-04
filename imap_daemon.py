#!/usr/bin/env python3
"""IMAP Daemon — Synchronisation Gmail temps réel + stockage mailstore.
Partage la DB mailstore avec MailApp V3.

Usage:
  source ~/.mailapp.env && python3 imap_daemon.py
"""

import imaplib
import os, signal, sys, time, logging
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from mailstore import init_db, store_email, get_connection

# ─── Config ────────────────────────────────────────────────────────────────
IMAP_HOST = 'imap.gmail.com'
IMAP_PORT = 993
IMAP_USER = os.environ.get('MAILAPP_IMAP_USER', 'truc.nguyen@scingenierie.fr')
IMAP_PASS = os.environ.get('MAILAPP_IMAP_PASS', '')
MAILBOXES = ['INBOX', '"[Gmail]/Sent Mail"', '[Gmail]/Drafts']
INITIAL_SYNC_DAYS = 2   # On a déjà tout migré → juste les 2 derniers jours
BATCH_SIZE = 20
RECONNECT_DELAY = 10

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [IMAP] %(message)s', datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger('imap-daemon')

running = True
signal.signal(signal.SIGINT, lambda s, f: setattr(sys.modules[__name__], 'running', False))
signal.signal(signal.SIGTERM, lambda s, f: setattr(sys.modules[__name__], 'running', False))


# ─── IMAP Connection ────────────────────────────────────────────────────────
def connect():
    if not IMAP_PASS:
        log.error("MAILAPP_IMAP_PASS non défini. Source ~/.mailapp.env d'abord.")
        sys.exit(1)
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(IMAP_USER, IMAP_PASS)
    log.info(f"Connecté: {IMAP_USER}")
    return conn


# ─── UID Tracking ───────────────────────────────────────────────────────────
def get_stored_uid(mailbox):
    conn = get_connection()
    row = conn.execute("SELECT last_uid FROM sync_state WHERE mailbox = ?",
                       (mailbox,)).fetchone()
    return row['last_uid'] if row else 0

def set_stored_uid(mailbox, uid):
    from mailstore import tx
    with tx() as db:
        db.execute("INSERT OR REPLACE INTO sync_state (mailbox, last_uid, last_sync) VALUES (?, ?, ?)",
                   (mailbox, uid, datetime.now(timezone.utc).isoformat()))


# ─── Email Processing ───────────────────────────────────────────────────────
def process_email(raw, mailbox, labels=None):
    labels = labels or []
    if mailbox != 'INBOX':
        labels.append(mailbox.replace('[Gmail]/', '').lower())
    try:
        result = store_email(raw, labels=labels)
        if result.get('stored'):
            log.info(f"📥 {result.get('sender','?')[:30]} | {result.get('subject','?')[:50]}")
            if result.get('project_code'):
                log.info(f"   🔗 {result['project_code']}")
            # Marquer comme envoyé si l'expéditeur est l'utilisateur
            if mailbox == 'INBOX' and result.get('sender') == IMAP_USER:
                conn_db = get_connection()
                conn_db.execute(
                    "UPDATE emails SET labels = labels || ' sent' WHERE hash = ? AND labels NOT LIKE '%sent%'",
                    (result['hash'],)
                )
                conn_db.commit()
                log.info(f"   📤 Auto-marqué comme envoyé")
            return True
        return False
    except Exception as e:
        log.error(f"Erreur stockage: {e}")
        return False


# ─── Sync Mailbox ───────────────────────────────────────────────────────────
def sync_mailbox(conn, mailbox, full_sync=False):
    conn.select(mailbox, readonly=True)
    last_uid = get_stored_uid(mailbox)

    if full_sync and last_uid == 0:
        since = (datetime.now() - timedelta(days=INITIAL_SYNC_DAYS)).strftime('%d-%b-%Y')
        criterion = f'(SINCE {since})'
        log.info(f"   Première sync [{mailbox}]: depuis {since}")
    elif last_uid > 0:
        criterion = f'UID {last_uid + 1}:*'
    else:
        criterion = 'ALL'

    status, data = conn.uid('search', None, criterion)
    if status != 'OK' or not data[0]:
        return
    uids = data[0].split()
    if not uids:
        return

    log.info(f"📬 {mailbox}: {len(uids)} emails à vérifier")
    count, max_uid = 0, last_uid

    for i in range(0, len(uids), BATCH_SIZE):
        batch = uids[i:i + BATCH_SIZE]
        try:
            status, fetch_data = conn.uid('fetch', b','.join(batch), '(RFC822)')
            if status != 'OK':
                continue
        except imaplib.IMAP4.error:
            log.warning(f"Batch fetch error, skip")
            continue

        bi = 0
        for item in fetch_data:
            if isinstance(item, tuple) and len(item) >= 2:
                raw = item[1]
                if isinstance(raw, bytes) and len(raw) > 200:
                    try:
                        if process_email(raw, mailbox):
                            count += 1
                        if bi < len(batch):
                            max_uid = max(max_uid, int(batch[bi]))
                    except (ValueError, IndexError):
                        pass
                    bi += 1

    if max_uid > last_uid:
        set_stored_uid(mailbox, max_uid)
    log.info(f"✅ {mailbox}: {count} nouveaux stockés")


# ─── Poll Loop (fallback: imaplib Python 3.9 n'a pas IDLE) ──────────────
def poll_loop(conn, mailbox='INBOX'):
    log.info(f"🔄 Polling activé sur {mailbox} (toutes les 60s)")
    while running:
        try:
            time.sleep(60)
            conn.noop()  # Keep connection alive
            conn.select(mailbox, readonly=True)
            last_uid = get_stored_uid(mailbox)
            status, data = conn.uid('search', None, f'UID {last_uid + 1}:*')
            if status == 'OK' and data[0]:
                new = len(data[0].split())
                if new > 0:
                    log.info(f"🔔 {new} nouveau(x) message(s)")
                    sync_mailbox(conn, mailbox)
        except imaplib.IMAP4.abort:
            log.warning("Connexion perdue")
            break
        except Exception as e:
            log.error(f"Erreur poll: {e}")
            time.sleep(5)


# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    log.info("=== IMAP Daemon — Démarrage ===")
    init_db()

    while running:
        conn = None
        try:
            conn = connect()
            for mbox in MAILBOXES:
                sync_mailbox(conn, mbox, full_sync=True)
            log.info("✅ Sync initiale terminée. Monitoring IDLE...")
            poll_loop(conn, 'INBOX')
        except imaplib.IMAP4.error as e:
            log.error(f"Erreur IMAP: {e}")
        except Exception:
            log.exception("Erreur inattendue")
        finally:
            try:
                if conn:
                    conn.logout()
            except Exception:
                pass
        if running:
            log.info(f"Reconnexion dans {RECONNECT_DELAY}s...")
            time.sleep(RECONNECT_DELAY)
    log.info("=== IMAP Daemon — Arrêt ===")


if __name__ == '__main__':
    main()
