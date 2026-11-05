from datetime import datetime
from flask import url_for
from db import query, execute
from mailer import send_email
from models.user import User


class Announcement:
    """Mga anunsyo ng paaralan. Ang Admin, Registrar at Finance ang nagpo-post; nakikita ng bawat role ang para sa kanya."""

    AUDIENCES = (('everyone', 'Everyone (all accounts and the landing page)'), ('applicant', 'Applicants'),
                 ('student', 'Students'), ('faculty', 'Faculty'), ('registrar', 'Registrar'), ('finance', 'Finance'))
    LIVE = "a.deleted_at IS NULL AND a.publish_at <= NOW() AND (a.expires_at IS NULL OR a.expires_at >= NOW())"
    STATE = ("CASE WHEN a.publish_at > NOW() THEN 'Scheduled' "
             "WHEN a.expires_at IS NOT NULL AND a.expires_at < NOW() THEN 'Expired' ELSE 'Live' END")
    FROM = "FROM announcements a LEFT JOIN users u ON u.id = a.created_by"
    FIELDS = "a.*, u.first_name, u.last_name"

    # ---------- para sa mga mambabasa ----------
    @classmethod
    def count_for(cls, role):
        return query(f"SELECT COUNT(*) AS n {cls.FROM} WHERE {cls.LIVE} AND a.audience IN ('everyone', %s)",
                     (role,), one=True)['n']

    @classmethod
    def for_role(cls, role, limit=10, offset=0):
        return query(f"SELECT {cls.FIELDS} {cls.FROM} WHERE {cls.LIVE} AND a.audience IN ('everyone', %s) "
                     "ORDER BY a.is_pinned DESC, a.publish_at DESC, a.id DESC LIMIT %s OFFSET %s",
                     (role, limit, offset))

    @classmethod
    def public(cls, limit=4):
        """Para sa landing page: ang para sa lahat lang."""
        return query(f"SELECT {cls.FIELDS} {cls.FROM} WHERE {cls.LIVE} AND a.audience = 'everyone' "
                     "ORDER BY a.is_pinned DESC, a.publish_at DESC, a.id DESC LIMIT %s", (limit,))

    # ---------- para sa mga nagpo-post ----------
    @classmethod
    def _where(cls, q='', state=''):
        where, params = ['a.deleted_at IS NULL'], []
        if state in ('Live', 'Scheduled', 'Expired'):
            where.append(f'{cls.STATE} = %s')
            params.append(state)
        if q:
            where.append('(a.title LIKE %s OR a.body LIKE %s)')
            params += [f'%{q}%'] * 2
        return ' AND '.join(where), params

    @classmethod
    def count(cls, q='', state=''):
        where, params = cls._where(q, state)
        return query(f'SELECT COUNT(*) AS n {cls.FROM} WHERE {where}', params, one=True)['n']

    @classmethod
    def rows(cls, q='', state='', limit=10, offset=0):
        where, params = cls._where(q, state)
        return query(f'SELECT {cls.FIELDS}, {cls.STATE} AS state {cls.FROM} WHERE {where} '
                     'ORDER BY a.is_pinned DESC, a.publish_at DESC, a.id DESC LIMIT %s OFFSET %s',
                     params + [limit, offset])

    @classmethod
    def find(cls, announcement_id):
        return query(f'SELECT {cls.FIELDS}, {cls.STATE} AS state {cls.FROM} '
                     'WHERE a.id = %s AND a.deleted_at IS NULL', (announcement_id,), one=True)

    @staticmethod
    def to_form(row):
        fmt = '%Y-%m-%dT%H:%M'
        return {'title': row['title'], 'body': row['body'], 'audience': row['audience'],
                'is_pinned': '1' if row['is_pinned'] else '',
                'publish_at': row['publish_at'].strftime(fmt) if row['publish_at'] else '',
                'expires_at': row['expires_at'].strftime(fmt) if row['expires_at'] else ''}

    # ---------- pagsusuri ----------
    @classmethod
    def clean(cls, form):
        data, errors = {}, []
        title = ' '.join(form.get('title', '').split())
        if not 3 <= len(title) <= 150:
            errors.append('The title must be 3 to 150 characters.')
        data['title'] = title
        body = form.get('body', '').strip()
        if not 3 <= len(body) <= 3000:
            errors.append('The message must be 3 to 3000 characters.')
        data['body'] = body
        audience = form.get('audience', '')
        if audience not in {k for k, _ in cls.AUDIENCES}:
            errors.append('Choose who the announcement is for.')
        data['audience'] = audience
        data['is_pinned'] = 1 if form.get('is_pinned') == '1' else 0

        parsed = {}
        for key, label in (('publish_at', 'publish'), ('expires_at', 'expiry')):
            raw = form.get(key, '').strip()
            parsed[key] = None
            if raw:
                try:
                    parsed[key] = datetime.strptime(raw, '%Y-%m-%dT%H:%M')
                except ValueError:
                    errors.append(f'Enter a valid {label} date and time.')
        if parsed['expires_at'] and parsed['expires_at'] <= (parsed['publish_at'] or datetime.now()):
            errors.append('The expiry must be after the publish time.')
        data.update(parsed)
        return data, errors

    # ---------- pag-save ----------
    @staticmethod
    def create(data, by_user):
        return execute("INSERT INTO announcements (title, body, audience, is_pinned, publish_at, expires_at, created_by) "
                       "VALUES (%s, %s, %s, %s, COALESCE(%s, NOW()), %s, %s)",
                       (data['title'], data['body'], data['audience'], data['is_pinned'], data['publish_at'],
                        data['expires_at'], by_user.id))

    @staticmethod
    def update(announcement_id, data):
        execute("UPDATE announcements SET title = %s, body = %s, audience = %s, is_pinned = %s, "
                "publish_at = COALESCE(%s, publish_at), expires_at = %s WHERE id = %s",
                (data['title'], data['body'], data['audience'], data['is_pinned'], data['publish_at'],
                 data['expires_at'], announcement_id))

    @staticmethod
    def delete(announcement_id):
        execute("UPDATE announcements SET deleted_at = NOW() WHERE id = %s", (announcement_id,))

    # ---------- abiso ----------
    @classmethod
    def notify(cls, data, with_email):
        """Dashboard notice sa lahat ng nasa audience (isang SQL). Ang email ay opsyonal at hanggang 100 lang.
        Ibinabalik ang (bilang ng na-abisuhan, bilang ng na-email o None kung hindi na-email)."""
        where, params = 'is_active = 1 AND is_activated = 1', []
        if data['audience'] != 'everyone':
            where += ' AND role = %s'
            params.append(data['audience'])
        total = query(f'SELECT COUNT(*) AS n FROM users WHERE {where}', params, one=True)['n']
        execute(f"INSERT INTO notifications (user_id, title, message) SELECT id, %s, %s FROM users WHERE {where}",
                [('Announcement: ' + data['title'])[:120], data['body'][:500]] + params)
        emailed = None
        if with_email and total <= 100:
            emailed = 0
            link = url_for('dashboard.home', _external=True)
            for row in query(f'SELECT id FROM users WHERE {where}', params):
                user = User.find(row['id'])
                if user and send_email('SIT announcement: ' + data['title'], user.email, 'notice', user=user,
                                       heading=data['title'], message=data['body'][:500], details=[],
                                       checklist=[], link=link):
                    emailed += 1
        return total, emailed