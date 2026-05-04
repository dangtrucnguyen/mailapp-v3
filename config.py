"""MailApp V3 — Configuration"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Database
DATABASE = os.path.join(DATA_DIR, 'mailapp.db')

# JWT
SECRET_KEY = os.environ.get('MAILAPP_SECRET', 'dev-secret-change-in-production-v3')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRE_MINUTES = 60 * 8  # 8 hours

# App
APP_HOST = '0.0.0.0'
APP_PORT = 6000
APP_NAME = 'MailApp V3'
APP_URL = os.environ.get('MAILAPP_URL', 'https://app.scigroup.fr:6000')

# Email (SMTP Gmail)
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'truc.nguyen@scingenierie.fr'
SMTP_PASS = os.environ.get('MAILAPP_SMTP_PASS', '')
SMTP_FROM = 'Truc NGUYEN <truc.nguyen@scingenierie.fr>'

# Sécurité
CSRF_ENABLED = True
