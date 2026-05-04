#!/bin/bash
# Start IMAP daemon in background (tmux session)
source ~/.mailapp.env
cd /home/sci/.openclaw/workspace/mailapp-v3

echo "[$(date)] Starting IMAP daemon..."
python3 imap_daemon.py >> /tmp/imap-daemon.log 2>&1
