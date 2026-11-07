from flask import request
from db import query, execute
from models.audit_log import AuditLog


class Privacy:
    """Data Privacy Notice at ang talaan ng pagtanggap (RA 10173). Kapag nagbago ang VERSION, tatanggapin ito ulit ng lahat."""

    VERSION = '2026-11'

    @classmethod
    def has_accepted(cls, user_id):
        return query("SELECT id FROM consent_logs WHERE user_id = %s AND policy_version = %s",
                     (user_id, cls.VERSION), one=True) is not None

    @classmethod
    def accept(cls, user):
        """Itinatala ang pagtanggap (isang beses lang bawat bersyon). Ibinabalik ang True kung bago."""
        if cls.has_accepted(user.id):
            return False
        execute("INSERT INTO consent_logs (user_id, policy_version, ip_address) VALUES (%s, %s, %s)",
                (user.id, cls.VERSION, request.remote_addr))
        AuditLog.record('Privacy notice accepted', f'Version {cls.VERSION}', user_id=user.id)
        return True

    @staticmethod
    def history(user_id):
        return query("SELECT policy_version, ip_address, accepted_at FROM consent_logs "
                     "WHERE user_id = %s ORDER BY id DESC", (user_id,))