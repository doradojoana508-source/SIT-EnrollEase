from flask import render_template, current_app
from flask_mail import Mail, Message
from models.email_log import EmailLog

mail = Mail()


def send_email(subject, recipient, template, **context):
    """Nagpapadala ng HTML at plain-text na email. Ibinabalik ang True/False; hindi nagka-crash ang page kapag pumalya.
    Itinatala ang bawat subok sa Email Log (Sent, Failed o Skipped)."""
    if not current_app.config.get('MAIL_PASSWORD'):
        current_app.logger.warning('Email not sent: MAIL_PASSWORD is not set in config.py')
        EmailLog.record(recipient, subject, template, 'Skipped', 'MAIL_PASSWORD is not set in config.py')
        return False
    try:
        msg = Message(subject, recipients=[recipient])
        msg.html = render_template(f'email/{template}.html', **context)
        msg.body = render_template(f'email/{template}.txt', **context)
        mail.send(msg)
        EmailLog.record(recipient, subject, template, 'Sent')
        return True
    except Exception as exc:                          # walang internet, maling password, atbp.
        current_app.logger.error('Email failed: %s', exc)
        EmailLog.record(recipient, subject, template, 'Failed', exc)
        return False