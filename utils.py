import time
from functools import wraps
from flask import g, session, redirect, url_for, flash, abort, request
from models.audit_log import AuditLog

# role -> pangalan ng blueprint ng portal niya (ang applicant ay nasa public site)
PORTAL_ROLES = {
    'student': 'portal',
    'admin': 'admin',
    'registrar': 'registrar',
    'finance': 'finance',
    'faculty': 'faculty',
}


def login_url_for(role, open_modal=True):
    """Saan ang login page ng role na ito."""
    key = PORTAL_ROLES.get(role)
    if key:
        return url_for(f'{key}.login')
    return url_for('public.index', auth='login') if open_modal else url_for('public.index')


def home_url_for(role):
    """Saan ang dashboard ng role na ito."""
    key = PORTAL_ROLES.get(role)
    return url_for(f'{key}.dashboard') if key else url_for('applicant.dashboard')


def start_session(user, remember=False):
    """Bagong session pagkatapos ng tamang login (iwas session fixation)."""
    user.record_login()
    session.clear()
    session['user_id'] = user.id
    session['session_version'] = user.session_version
    session['remember'] = remember
    session['last_seen'] = int(time.time())
    session.permanent = remember
    AuditLog.record('Login', user_id=user.id)


def _login_redirect():
    flash('Please log in to continue.', 'info')
    key = (request.blueprint or '').split('_')[0]        # 'admin_users' -> 'admin'
    if key in PORTAL_ROLES.values():
        return redirect(url_for(f'{key}.login'))
    return redirect(url_for('public.index', auth='login'))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return _login_redirect()
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return _login_redirect()
            if g.user.role not in roles:
                abort(403)                                # mali ang role: bawal
            return view(*args, **kwargs)
        return wrapped
    return decorator

class Pager:
    """Pagination para sa kahit anong listahan."""

    def __init__(self, total, page, per_page=10):
        self.total = total
        self.per_page = per_page
        self.pages = max(1, -(-total // per_page))
        self.page = min(max(page, 1), self.pages)
        self.args = {k: v for k, v in request.args.items() if k != 'page'}   # panatilihin ang search/filter

    @property
    def start(self):
        return (self.page - 1) * self.per_page + 1 if self.total else 0

    @property
    def end(self):
        return min(self.page * self.per_page, self.total)