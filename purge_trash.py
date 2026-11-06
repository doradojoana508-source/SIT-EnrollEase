"""Manual na paglilinis ng basurahan at lumang email log: python purge_trash.py
(Awtomatiko rin itong tumatakbo tuwing bubuksan ng Admin ang Trash Bin at ang Email Log.)"""
from app import app
from models.email_log import EmailLog
from models.trash import Trash

with app.app_context():
    print(f'Removed {Trash.purge_expired()} item(s) older than {Trash.DAYS} days from the Trash Bin.')
    EmailLog.purge_old()
    print(f'Removed email log entries older than {EmailLog.RETENTION_DAYS} days.')