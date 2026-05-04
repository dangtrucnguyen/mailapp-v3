"""MailApp V3 Phase 5 — Service Web Push (VAPID)"""
import json
import os
from config import DATA_DIR

VAPID_KEYS_FILE = os.path.join(DATA_DIR, 'vapid_keys.json')

def generate_vapid_keys():
    """Generate VAPID keys for Web Push if they don't exist"""
    if os.path.exists(VAPID_KEYS_FILE):
        with open(VAPID_KEYS_FILE) as f:
            return json.load(f)

    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from base64 import urlsafe_b64encode

    key = ec.generate_private_key(ec.SECP256R1())
    private_bytes = key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )

    # Convert to urlsafe base64 without padding
    private_b64 = urlsafe_b64encode(private_bytes).rstrip(b'=').decode()
    public_b64 = urlsafe_b64encode(public_bytes).rstrip(b'=').decode()

    keys = {
        'public_key': public_b64,
        'private_key': private_b64,
        'subject': 'mailto:truc.nguyen@scingenierie.fr'
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(VAPID_KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)
    return keys

def get_vapid_keys():
    if os.path.exists(VAPID_KEYS_FILE):
        with open(VAPID_KEYS_FILE) as f:
            return json.load(f)
    return generate_vapid_keys()

def send_push_notification(subscription: dict, title: str, body: str, url: str = '/',
                           vapid_keys: dict = None) -> bool:
    """Send a Web Push notification to a single subscription"""
    try:
        from pywebpush import webpush, WebPushException

        if vapid_keys is None:
            vapid_keys = get_vapid_keys()

        data = json.dumps({
            'title': title,
            'body': body,
            'url': url,
            'icon': '/icon-192.png',
            'badge': '/icon-192.png'
        })

        webpush(
            subscription_info=subscription,
            data=data,
            vapid_private_key=vapid_keys['private_key'],
            vapid_claims={'sub': vapid_keys['subject']}
        )
        return True
    except Exception as e:
        print(f"Push notification error: {e}")
        return False

def notify_user(user_id: int, title: str, body: str, url: str = '/',
                db=None) -> int:
    """Send push notifications to all devices of a user.
    Returns number of notifications sent.
    """
    if db is None:
        from database import get_sync_db
        db = get_sync_db()
        own_db = True
    else:
        own_db = False

    try:
        subs = db.execute(
            'SELECT subscription_json FROM push_subscriptions WHERE user_id = ?',
            (user_id,)
        ).fetchall()

        keys = get_vapid_keys()
        sent = 0
        for sub in subs:
            subscription = json.loads(sub['subscription_json'])
            if send_push_notification(subscription, title, body, url, keys):
                sent += 1
        return sent
    finally:
        if own_db:
            db.close()
