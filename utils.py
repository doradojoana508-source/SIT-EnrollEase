from functools import wraps
from flask import g, flash, redirect, url_for, abort


def login_required(view):
    """Pinipigilan ang mga hindi naka-login at ibinabalik sila sa login modal."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get('user') is None:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('public.index', auth='login'))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    """Para lang sa mga role na nakalista, halimbawa @roles_required('admin', 'registrar')."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator