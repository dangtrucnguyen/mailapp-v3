#!/usr/bin/env python3
"""Migre TOUS les emails V1 (mailbox folder-per-email) → mailstore content-addressed.
Puis nettoie l'ancienne table emails dans mailapp.db."""

import sys
import os
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from mailstore import init_db, store_email, stats

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('migrate')

MAILBOX_DIR = Path('/home/sci/.openclaw/workspace/mailbox/data')
OLD_DB = Path('data/mailapp.db')


def find_emails(base: Path):
    """Find all email.eml files in V1 folder-per-email structure."""
    for root, dirs, files in os.walk(base):
        for f in files:
            if f == 'email.eml':
                yield Path(root) / f


def main():
    init_db()

    eml_files = list(find_emails(MAILBOX_DIR))
    log.info(f"Found {len(eml_files)} emails in V1")

    stored = 0
    duplicates = 0
    errors = 0

    for i, path in enumerate(eml_files):
        try:
            raw = path.read_bytes()
            result = store_email(raw, labels=['V1-migrated'])
            log.info(f"[{i+1}/{len(eml_files)}] {path.parent.name[:60]}")
            if result.get('stored'):
                log.info(f"  → hash={result['hash'][:12]}... | {result.get('subject','?')[:50]}")
                if result.get('project_code'):
                    log.info(f"  🔗 {result['project_code']}")
                stored += 1
            else:
                log.info(f"  ↪ doublon ({result.get('reason','?')})")
                duplicates += 1
        except Exception as e:
            log.error(f"  ✗ ERROR: {e}")
            errors += 1

    log.info(f"\n=== Done ===")
    log.info(f"  Stored:  {stored} new")
    log.info(f"  Skipped: {duplicates} duplicates")
    log.info(f"  Errors:  {errors}")
    log.info(f"  Total:   {stats()}")


def cleanup_old():
    """Clean old emails table in mailapp.db (keep all other tables)."""
    db = sqlite3.connect(str(OLD_DB))
    before = db.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    db.execute("DELETE FROM emails")
    db.commit()
    after = db.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    log.info(f"\n=== Nettoyage mailapp.db ===")
    log.info(f"  emails avant: {before}")
    log.info(f"  emails après: {after}")
    db.close()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--cleanup', action='store_true', help='Vider la table emails dans mailapp.db')
    args = ap.parse_args()

    main()

    if args.cleanup:
        cleanup_old()

    log.info("\n✅ Migration terminée")
