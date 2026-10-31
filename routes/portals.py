from flask import Blueprint, render_template, redirect, url_for, request, flash, g
from models.user import User
from mailer import send_email
from utils import roles_required, start_session
from models.stats import Stats

# Isang config bawat portal. Ang key ang pangalan ng blueprint.
PORTALS = {
    'portal':    {'prefix': '/portal',    'role': 'student',   'title': 'Student Portal',
                  'icon': 'bi-mortarboard-fill', 'login_by': 'student_id',
                  'field_label': 'Student ID', 'placeholder': 'Student ID (e.g. 23-1-0096)'},
    'admin':     {'prefix': '/admin',     'role': 'admin',     'title': 'Administrator',
                  'icon': 'bi-shield-lock-fill', 'login_by': 'email',
                  'field_label': 'Email', 'placeholder': 'Email address'},
    'registrar': {'prefix': '/registrar', 'role': 'registrar', 'title': 'Registrar',
                  'icon': 'bi-journal-check', 'login_by': 'email',
                  'field_label': 'Email', 'placeholder': 'Email address'},
    'finance':   {'prefix': '/finance',   'role': 'finance',   'title': 'Finance',
                  'icon': 'bi-cash-coin', 'login_by': 'email',
                  'field_label': 'Email', 'placeholder': 'Email address'},
    'faculty':   {'prefix': '/faculty',   'role': 'faculty',   'title': 'Faculty',
                  'icon': 'bi-person-workspace', 'login_by': 'email',
                  'field_label': 'Email', 'placeholder': 'Email address'},
}


def find_account(cfg, identifier):
    """Hinahanap ang account PARA SA portal na ito lang. Mali ang portal = parang walang account."""
    if not identifier:
        return None
    user = User.find_by_login(identifier)
    if user is None or user.role != cfg['role']:
        return None
    if cfg['login_by'] == 'student_id' and (user.username or '').lower() != identifier:
        return None                                    # student: Student ID lang, hindi email
    if cfg['login_by'] == 'email' and user.email != identifier:
        return None
    return user


def create_portal(key, cfg):
    bp = Blueprint(key, __name__, url_prefix=cfg['prefix'])

    def page(mode='login'):
        return render_template('portal/login.html', cfg=cfg, key=key, mode=mode, form=request.form)

    @bp.route('/login', methods=['GET', 'POST'])
    def login():
        if g.user and g.user.role == cfg['role']:
            return redirect(url_for(f'{key}.dashboard'))
        if request.method == 'GET':
            return page()

        identifier = request.form.get('identifier', '').strip().lower()
        password = request.form.get('password', '')
        user = find_account(cfg, identifier)

        if user and user.is_locked():
            flash('Too many failed attempts. Please try again in 15 minutes.', 'danger')
            return page()
        if user is None or not user.check_password(password):
            if user:
                user.register_failed_login()
            flash('Incorrect login details.', 'danger')
            return page()
        if not user.is_active:
            flash('This account has been deactivated. Please contact the school.', 'danger')
            return page()
        if not user.is_activated:
            flash('Your account is not yet activated. Please use the activation link sent by the school.', 'warning')
            return page()

        start_session(user)                                   # walang Remember me sa portal: 30 min idle timeout
        return redirect(url_for(f'{key}.dashboard'))

    @bp.route('/forgot', methods=['GET', 'POST'])
    def forgot():
        if request.method == 'POST':
            user = find_account(cfg, request.form.get('identifier', '').strip().lower())
            if user and user.is_active and user.is_activated:
                link = url_for('auth.reset', token=user.get_reset_token(), _external=True)
                send_email('Reset your SIT-EnrollEase password', user.email, 'reset', user=user, link=link)
            flash('If that account exists, a password reset link has been sent to its email.', 'info')
            return redirect(url_for(f'{key}.login'))
        return page('forgot')

    @bp.route('/dashboard')
    @roles_required(cfg['role'])
    def dashboard():
        if key == 'registrar':
            return render_template('registrar/dashboard.html', **Stats.registrar(request.args.get('term', type=int)))
        return render_template('app_home.html', heading=cfg['title'])

    return bp