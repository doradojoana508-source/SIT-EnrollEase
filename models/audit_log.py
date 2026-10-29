from flask import g, request
from db import query, execute


class AuditLog:
    """Talaan kung sino ang gumawa ng ano, kailan, at mula sa anong IP."""

    @staticmethod
    def record(action, details=None, user_id=None):
        actor = user_id or (g.user.id if g.get('user') else None)
        execute(
            "INSERT INTO audit_logs (user_id, action, details, ip_address) VALUES (%s, %s, %s, %s)",
            (actor, action, details, request.remote_addr),
        )

    @staticmethod
    def search(q='', limit=15, offset=0):
        where, params = '', []
        if q:
            like = f'%{q}%'
            where = ("WHERE a.action LIKE %s OR a.details LIKE %s OR u.email LIKE %s "
                     "OR u.first_name LIKE %s OR u.last_name LIKE %s")
            params = [like] * 5
        base = f"FROM audit_logs a LEFT JOIN users u ON u.id = a.user_id {where}"
        total = query(f"SELECT COUNT(*) AS n {base}", params, one=True)['n']
        rows = query(
            f"SELECT a.*, u.first_name, u.last_name, u.email, u.role {base} "
            "ORDER BY a.id DESC LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        return rows, total