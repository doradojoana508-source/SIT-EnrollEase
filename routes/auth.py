import re
from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from models.user import User
from routes.public import home_context

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
NAME_RE = re.compile(r"^[A-Za-zÀ-ÿ .'\-]+$")
PASSWORD_RE = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{8,}$')
ACTIVATION_DAYS = 7


def show_home(auth_open):
    """Ipinapakita ang landing page na bukas ang modal, para makita ang mga error."""
    return render_template('public/index.html', auth_open=auth_open, form=request.form, **home_context())


def clean_name(value):
    return ' '.join(value.split())            # inaalis ang sobrang espasyo


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Pampublikong Register: applicant lang ang nagagawa rito."""
    if request.method == 'GET':
        return redirect(url_for('public.index', auth='register'))

    first = clean_name(request.form.get('first_name', ''))
    middle = clean_name(request.form.get('middle_name', ''))
    last = clean_name(request.form.get('last_name', ''))
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    confirm = request.form.get('confirm', '')
    agree = request.form.get('agree')

    errors = []
    if not (2 <= len(first) <= 50 and NAME_RE.match(first)):
        errors.append('First name must be 2 to 50 letters.')
    if middle and not (len(middle) <= 50 and NAME_RE.match(middle)):
        errors.append('Middle name may only contain letters, up to 50 characters.')
    if not (2 <= len(last) <= 50 and NAME_RE.match(last)):
        errors.append('Last name must be 2 to 50 letters.')
    if not EMAIL_RE.match(email) or len(email) > 120:
        errors.append('Please enter a valid email address.')
    if not PASSWORD_RE.match(password):
        errors.append('Password needs at least 8 characters with a letter and a number.')
    if password != confirm:
        errors.append('Passwords do not match.')
    if not agree:
        errors.append('You must agree to the Terms and the Data Privacy Notice.')
    if not errors and User.find_by_email(email):
        errors.append('That email is already registered.')

    if errors:
        for message in errors:
            flash(message, 'danger')
        return show_home('register')

    user = User(first, last, email, 'applicant', middle or None)
    user.set_password(password)               # naka-hash
    user.save()

    flash('Account created! You can now log in.', 'success')
    return redirect(url_for('public.index', auth='login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return redirect(url_for('public.index', auth='login'))

    identifier = request.form.get('identifier', '').strip().lower()   # email o Student ID
    password = request.form.get('password', '')
    user = User.find_by_login(identifier)

    if user and user.is_locked():
        flash('Too many failed attempts. Please try again in 15 minutes.', 'danger')
        return show_home('login')

    if user is None or not user.check_password(password):
        if user:
            user.register_failed_login()
        flash('Incorrect login details.', 'danger')      # iisang mensahe, hindi sinasabi kung alin ang mali
        return show_home('login')

    # Tama na ang password: ngayon lang sasabihin kung hindi pa activated o naka-deactivate
    if not user.is_activated:
        flash('Your account is not yet activated. Please use the activation link sent to you by the school.', 'warning')
        return show_home('login')
    if not user.is_active:
        flash('This account has been deactivated. Please contact the school.', 'danger')
        return show_home('login')

    user.record_login()
    session.clear()                                  # bagong session, iwas session fixation
    session['user_id'] = user.id
    session['session_version'] = user.session_version
    session.permanent = True                         # may timeout ayon sa app.py
    return redirect(url_for('dashboard.home'))       # papalitan ng redirect ayon sa role sa Hakbang 8


@auth_bp.route('/activate/<token>')
def activate(token):
    """Ang activation link na ipinapadala ng school. May bisa ng 7 araw."""
    user = User.from_token(token, 'activate', max_age=ACTIVATION_DAYS * 24 * 3600)
    if user is None:
        flash('This activation link is invalid or has expired. Please contact the school.', 'danger')
    elif user.is_activated:
        flash('This account is already activated. You can log in.', 'info')
    else:
        user.activate()
        flash('Your account is activated. You can now log in.', 'success')
    return redirect(url_for('public.index', auth='login'))


@auth_bp.route('/logout', methods=['POST'])         # POST, para hindi ma-logout ng isang link lang
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.index'))