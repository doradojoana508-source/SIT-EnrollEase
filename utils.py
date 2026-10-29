import time
from functools import wraps
from flask import g, session, redirect, url_for, flash, abort, request

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


def _login_redirect():
    flash('Please log in to continue.', 'info')
    if request.blueprint in PORTAL_ROLES.values():       # nasa loob ng portal: sa login ng portal na iyon
        return redirect(url_for(f'{request.blueprint}.login'))
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