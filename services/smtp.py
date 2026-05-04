"""MailApp V3 — Service SMTP (envoi d'emails)"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid

import config


def send_email(to: str, subject: str, body: str, body_html: str = None,
               cc: str = None, bcc: str = None, reply_to_message_id: str = None,
               attachments: list = None) -> dict:
    """Envoie un email via SMTP Gmail.
    Retourne {'ok': True, 'message_id': '...'} ou {'ok': False, 'error': '...'}
    """
    if not config.SMTP_PASS:
        return {'ok': False, 'error': 'SMTP non configuré (MAILAPP_SMTP_PASS non défini)'}

    msg = MIMEMultipart('alternative')
    msg['From'] = config.SMTP_FROM
    msg['To'] = to
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain='scingenierie.fr')

    if reply_to_message_id:
        msg['In-Reply-To'] = reply_to_message_id
        msg['References'] = reply_to_message_id
    if cc:
        msg['Cc'] = cc

    # Corps texte
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # Corps HTML (optionnel)
    if body_html:
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

    # Destinataires
    recipients = [to]
    if cc:
        recipients += [addr.strip() for addr in cc.split(',')]
    if bcc:
        recipients += [addr.strip() for addr in bcc.split(',')]

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASS)
            server.sendmail(config.SMTP_USER, recipients, msg.as_string())
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    return {'ok': True, 'message_id': msg['Message-ID']}
