from db import query, execute
from models.setting import Number


class EmailLog:
    """Talaan ng bawat email na sinubukang ipadala ng system. Hindi sine-save ang laman ng email
    (may mga link ng activation at reset), ang tatanggap, paksa at resulta lang."""

    STATUSES = ('Sent', 'Failed', 'Skipped')
    RETENTION_DAYS = Number('email_log_days', 180, 30, 365)

    @staticmethod
    def record(recipient, subject, template, status, error=None):
        """Hindi dapat pumalya ang pagpapadala dahil lang sa log, kaya nilululon ang anumang error."""
        try:
            execute("INSERT INTO email_logs (recipient, subject, template, status, error) VALUES (%s, %s, %s, %s, %s)",
                    (str(recipient)[:150], str(subject)[:200], str(template)[:40], status,
                     str(error)[:250] if error else None))
        except Exception:
            pass

    @classmethod
    def _where(cls, q='', status=''):
        where, params = ['1 = 1'], []
        if status in cls.STATUSES:
            where.append('status = %s')
            params.append(status)
        if q:
            where.append('(recipient LIKE %s OR subject LIKE %s OR template LIKE %s)')
            params += [f'%{q}%'] * 3
        return ' AND '.join(where), params

    @classmethod
    def count(cls, q='', status=''):
        where, params = cls._where(q, status)
        return query(f'SELECT COUNT(*) AS n FROM email_logs WHERE {where}', params, one=True)['n']

    @classmethod
    def rows(cls, q='', status='', limit=15, offset=0):
        where, params = cls._where(q, status)
        return query(f'SELECT * FROM email_logs WHERE {where} ORDER BY id DESC LIMIT %s OFFSET %s',
                     params + [limit, offset])

    @staticmethod
    def counts():
        rows = query('SELECT status, COUNT(*) AS n FROM email_logs GROUP BY status')
        return {r['status']: r['n'] for r in rows}

    @classmethod
    def purge_old(cls):
        execute('DELETE FROM email_logs WHERE created_at < NOW() - INTERVAL %s DAY', (cls.RETENTION_DAYS,))