import re
import time
from flask import Blueprint, render_template, redirect, url_for, request, session, flash, g
from models.user import User
from routes.public import home_context
from mailer import send_email
from utils import login_url_for

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
NAME_RE = re.compile(r"^[A-Za-zÀ-ÿ .'\-]+$")
PASSWORD_RE = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{8,}$')
ACTIVATION_DAYS = 7
VERIFY_HOURS = 24
RESET_HOURS = 1


def show_home(auth_open):
    """Ipinapakita ang landing page na bukas ang modal, para makita ang mga error."""
    return render_template('public/index.html', auth_open=auth_open, form=request.form, **home_context())


def clean_name(value):
    return ' '.join(value.split())            # inaalis ang sobrang espasyo


def send_verification(user):
    link = url_for('auth.verify', token=user.get_token('verify'), _external=True)
    return send_email('Verify your SIT-EnrollEase account', user.email, 'verify', user=user, link=link)


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

    if send_verification(user):
        flash(f'Account created! We sent a verification link to {email}. Please verify before logging in.', 'success')
    else:
        flash('Account created, but we could not send the verification email. '
              'Try logging in and we will send a new link.', 'warning')
    return redirect(url_for('public.index', auth='login'))


@auth_bp.route('/verify/<token>')
def verify(token):
    user = User.from_token(token, 'verify', max_age=VERIFY_HOURS * 3600)
    if user is None:
        flash('This verification link is invalid or has expired. Log in to receive a new one.', 'danger')
    else:
        if not user.is_verified:
            user.mark_verified()
        flash('Your email is verified. You can now log in.', 'success')
    return redirect(url_for('public.index', auth='login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login ng APPLICANT lang (email). Student at staff ay may sariling portal."""
    if request.method == 'GET':
        return redirect(url_for('public.index', auth='login'))

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    remember = bool(request.form.get('remember'))
    user = User.find_by_email(email) if email else None

    if user and user.is_locked():
        flash('Too many failed attempts. Please try again in 15 minutes.', 'danger')
        return show_home('login')

    if user is None or not user.check_password(password):
        if user:
            user.register_failed_login()
        flash('Incorrect login details.', 'danger')
        return show_home('login')

    if user.role != 'applicant':
        flash('Students and school staff sign in through their own portal, not through EnrollEase.', 'info')
        return show_home('login')
    if not user.is_active:
        flash('This account has been deactivated. Please contact the school.', 'danger')
        return show_home('login')
    if not user.is_verified:
        send_verification(user)
        flash('Please verify your email first. We just sent you a new verification link.', 'warning')
        return show_home('login')

    user.record_login()
    session.clear()
    session['user_id'] = user.id
    session['session_version'] = user.session_version
    session['remember'] = remember
    session['last_seen'] = int(time.time())
    session.permanent = remember
    return redirect(url_for('dashboard.home'))


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


@auth_bp.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'GET':
        return redirect(url_for('public.index', auth='forgot'))

    email = request.form.get('email', '').strip().lower()
    user = User.find_by_email(email) if email else None
    if user and user.role == 'applicant' and user.is_active:
        link = url_for('auth.reset', token=user.get_reset_token(), _external=True)
        send_email('Reset your SIT-EnrollEase password', user.email, 'reset', user=user, link=link)
    flash('If that account exists, a password reset link has been sent to its email.', 'info')
    return redirect(url_for('public.index', auth='login'))

@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset(token):
    user = User.from_reset_token(token, max_age=RESET_HOURS * 3600)
    if user is None:
        flash('This reset link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('public.index', auth='forgot'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        errors = []
        if not PASSWORD_RE.match(password):
            errors.append('Password needs at least 8 characters with a letter and a number.')
        if password != confirm:
            errors.append('Passwords do not match.')
        if errors:
            for message in errors:
                flash(message, 'danger')
            return render_template('auth/reset.html', token=token)

        user.set_password(password)
        user.failed_attempts = 0
        user.locked_until = None
        user.session_version += 1                    # ma-logout ang lahat ng device
        user.save()
        flash('Your password has been changed. Please log in.', 'success')
        return redirect(login_url_for(user.role))

    return render_template('auth/reset.html', token=token)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    role = g.user.role if g.user else None
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(login_url_for(role, open_modal=False) if role else url_for('public.index'))