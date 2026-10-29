from flask import url_for
from db import query, execute
from mailer import send_email


class Notification:
    """Notice sa dashboard at email, sabay. Gagamitin sa lahat ng pagbabago ng status."""

    @staticmethod
    def notify(user, subject, heading, message, details=None, checklist=None):
        execute("INSERT INTO notifications (user_id, title, message) VALUES (%s, %s, %s)",
                (user.id, heading[:120], message[:500]))
        link = url_for('dashboard.home', _external=True)
        return send_email(subject, user.email, 'notice', user=user, heading=heading, message=message,
                          details=details or [], checklist=checklist or [], link=link)

    @staticmethod
    def unread_for(user_id):
        return query("SELECT * FROM notifications WHERE user_id = %s AND is_read = 0 ORDER BY id DESC", (user_id,))

    @staticmethod
    def mark_read(notice_id, user_id):
        execute("UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s", (notice_id, user_id))

    @staticmethod
    def mark_all_read(user_id):
        execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (user_id,))