from datetime import datetime
from flask import request
from db import query, execute

LOCAL_IPS = ('127.0.0.1', '::1')                     # ang sarili mong computer ay hindi hinaharang (para sa testing)


class Security:
    """Pagsubaybay sa mga bigong login. May dalawang proteksyon:
    1) ang account ay naka-lock ng 15 minuto pagkatapos ng 5 maling password (nasa User model),
    2) ang IP address ay hinaharang ng 15 minuto kapag 10 beses nang pumalya sa loob ng 15 minuto (kahit anong account)."""

    IP_LIMIT = 10
    WINDOW_MINUTES = 15
    RETENTION_DAYS = 90
    TYPES = {'failed_login': ('Failed login', 'warning'), 'account_locked': ('Account locked', 'danger'),
             'locked_attempt': ('Tried a locked account', 'secondary'), 'ip_blocked': ('Blocked IP tried again', 'dark')}
    PORTAL_LABELS = {'applicant': 'Applicant', 'portal': 'Student', 'admin': 'Admin', 'registrar': 'Registrar',
                     'finance': 'Finance', 'faculty': 'Faculty'}

    # ---------- pagtatala (hindi dapat makasira sa login) ----------
    @staticmethod
    def record(event_type, portal, identifier, user=None):
        """Hindi kailanman sine-save ang password. Ang tinype na email o Student ID lang."""
        try:
            execute("INSERT INTO security_events (event_type, portal, identifier, user_id, ip_address) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (event_type, portal, (identifier or '')[:120] or None, user.id if user else None,
                     (request.remote_addr or '')[:45] or None))
        except Exception:
            pass

    @classmethod
    def ip_blocked(cls, ip=None):
        ip = ip or request.remote_addr
        if not ip or ip in LOCAL_IPS:
            return False
        try:
            n = query("SELECT COUNT(*) AS n FROM security_events WHERE ip_address = %s AND event_type = 'failed_login' "
                      "AND cleared = 0 AND created_at > NOW() - INTERVAL %s MINUTE", (ip, cls.WINDOW_MINUTES),
                      one=True)['n']
        except Exception:
            return False
        return n >= cls.IP_LIMIT

    # ---------- para sa Admin ----------
    @classmethod
    def summary(cls):
        def count(where):
            return query(f"SELECT COUNT(*) AS n FROM security_events WHERE {where}", one=True)['n']
        return {
            'failed_24h': count("event_type = 'failed_login' AND created_at > NOW() - INTERVAL 1 DAY"),
            'locks_24h': count("event_type = 'account_locked' AND created_at > NOW() - INTERVAL 1 DAY"),
            'blocked_24h': count("event_type = 'ip_blocked' AND created_at > NOW() - INTERVAL 1 DAY"),
            'events_7d': count("created_at > NOW() - INTERVAL 7 DAY"),
        }

    @staticmethod
    def locked_accounts():
        return query("SELECT id, first_name, last_name, email, username, role, locked_until FROM users "
                     "WHERE locked_until IS NOT NULL AND locked_until > %s ORDER BY locked_until DESC",
                     (datetime.now(),))

    @classmethod
    def blocked_ips(cls):
        rows = query("SELECT ip_address, COUNT(*) AS attempts, MAX(created_at) AS last_attempt FROM security_events "
                     "WHERE event_type = 'failed_login' AND cleared = 0 AND ip_address IS NOT NULL "
                     "AND created_at > NOW() - INTERVAL %s MINUTE GROUP BY ip_address HAVING COUNT(*) >= %s "
                     "ORDER BY last_attempt DESC", (cls.WINDOW_MINUTES, cls.IP_LIMIT))
        return [r for r in rows if r['ip_address'] not in LOCAL_IPS]

    @staticmethod
    def unblock_ip(ip):
        execute("UPDATE security_events SET cleared = 1 WHERE ip_address = %s AND event_type = 'failed_login' "
                "AND cleared = 0", (ip,))

    @staticmethod
    def top_ips():
        """Mga IP na pinakamaraming pumalya sa nakaraang 24 oras."""
        return query("SELECT ip_address, COUNT(*) AS attempts, COUNT(DISTINCT identifier) AS accounts, "
                     "MAX(created_at) AS last_attempt FROM security_events WHERE event_type = 'failed_login' "
                     "AND ip_address IS NOT NULL AND created_at > NOW() - INTERVAL 1 DAY GROUP BY ip_address "
                     "ORDER BY attempts DESC, last_attempt DESC LIMIT 5")

    @classmethod
    def _where(cls, q='', kind=''):
        where, params = ['1 = 1'], []
        if kind in cls.TYPES:
            where.append('e.event_type = %s')
            params.append(kind)
        if q:
            where.append('(e.identifier LIKE %s OR e.ip_address LIKE %s)')
            params += [f'%{q}%'] * 2
        return ' AND '.join(where), params

    @classmethod
    def count(cls, q='', kind=''):
        where, params = cls._where(q, kind)
        return query(f'SELECT COUNT(*) AS n FROM security_events e WHERE {where}', params, one=True)['n']

    @classmethod
    def rows(cls, q='', kind='', limit=15, offset=0):
        where, params = cls._where(q, kind)
        return query("SELECT e.*, u.first_name, u.last_name FROM security_events e "
                     f"LEFT JOIN users u ON u.id = e.user_id WHERE {where} ORDER BY e.id DESC LIMIT %s OFFSET %s",
                     params + [limit, offset])

    @classmethod
    def purge_old(cls):
        execute('DELETE FROM security_events WHERE created_at < NOW() - INTERVAL %s DAY', (cls.RETENTION_DAYS,))