import re
import secrets
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models.user import User
from models.audit_log import AuditLog
from mailer import send_email
from routes.auth import EMAIL_RE, NAME_RE, clean_name
from utils import roles_required, Pager

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin/users')

STAFF_ROLES = ('registrar', 'finance', 'faculty')
FILTER_ROLES = ('applicant', 'student') + STAFF_ROLES
STUDENT_ID_RE = re.compile(r'^\d{2}-[1-3]-\d{4}$')      # YY-trimester-NNNN, hal. 23-1-0096
PER_PAGE = 10


def person_errors(first, middle, last, email):
    errors = []
    if not (2 <= len(first) <= 50 and NAME_RE.match(first)):
        errors.append('First name must be 2 to 50 letters.')
    if middle and not (len(middle) <= 50 and NAME_RE.match(middle)):
        errors.append('Middle name may only contain letters, up to 50 characters.')
    if not (2 <= len(last) <= 50 and NAME_RE.match(last)):
        errors.append('Last name must be 2 to 50 letters.')
    if not EMAIL_RE.match(email) or len(email) > 120:
        errors.append('Please enter a valid email address.')
    return errors


def send_activation(user):
    link = url_for('auth.activate', token=user.get_token('activate'), _external=True)
    return send_email('Activate your SIT-EnrollEase account', user.email, 'activate', user=user, link=link)


def get_target(user_id):
    """Ang account na gagalawin. Hindi pwedeng galawin ng UI ang admin account."""
    user = User.find(user_id)
    if user is None:
        abort(404)
    if user.role == 'admin':
        abort(403)
    return user


@admin_users_bp.route('/')
@roles_required('admin')
def index():
    q = request.args.get('q', '').strip()
    role = request.args.get('role', '')
    if role not in FILTER_ROLES:
        role = ''
    page = request.args.get('page', 1, type=int)
    users, total = User.search(q, role, PER_PAGE, (max(page, 1) - 1) * PER_PAGE)
    pager = Pager(total, page, PER_PAGE)
    return render_template('admin/users.html', users=users, pager=pager, q=q, role=role, roles=FILTER_ROLES)


@admin_users_bp.route('/new', methods=['GET', 'POST'])
@roles_required('admin')
def create():
    today = date.today().isoformat()
    if request.method == 'GET':
        return render_template('admin/user_form.html', mode='create', form={}, today=today)

    f = request.form
    role = f.get('role', '')
    first = clean_name(f.get('first_name', ''))
    middle = clean_name(f.get('middle_name', ''))
    last = clean_name(f.get('last_name', ''))
    email = f.get('email', '').strip().lower()
    student_id = f.get('student_id', '').strip()
    birthdate = f.get('birthdate', '').strip()

    errors = person_errors(first, middle, last, email)
    if role not in STAFF_ROLES + ('student',):
        errors.append('Choose a valid role.')

    existing = User.find_by_email(email) if EMAIL_RE.match(email) else None
    initial_password = None
    if role == 'student':
        if not STUDENT_ID_RE.match(student_id):
            errors.append('Student ID must look like 23-1-0096 (year, trimester 1-3, number).')
        elif User.find_by_username(student_id):
            errors.append('That Student ID is already assigned to another account.')
        try:
            born = datetime.strptime(birthdate, '%Y-%m-%d').date()
            if born >= date.today():
                raise ValueError
            initial_password = born.strftime('%y/%m/%d')       # YY/MM/DD
        except ValueError:
            errors.append('Enter a valid birth date.')
        if existing and existing.role != 'applicant':
            errors.append('That email already belongs to another account.')
    elif existing:
        errors.append('That email already belongs to another account.')

    if errors:
        for message in errors:
            flash(message, 'danger')
        return render_template('admin/user_form.html', mode='create', form=f, today=today)

    if role == 'student' and existing:                          # applicant -> student
        existing.update_details(first, middle or None, last, email)
        existing.promote_to_student(student_id, initial_password)
        user = User.find_by_email(email)
        AuditLog.record('Applicant promoted to student', f'{email} -> {student_id}')
    else:
        user = User(first, last, email, role, middle or None)
        if role == 'student':
            user.username = student_id
            user.set_password(initial_password)
        else:
            user.set_password(secrets.token_urlsafe(24))       # pansamantala; sila ang pipili sa activation
        user.is_activated = 0
        user.save()
        user = User.find_by_email(email)
        AuditLog.record('Account created', f'{role}: {student_id or email}')

    if send_activation(user):
        flash(f'Account created. An activation link was sent to {email}.', 'success')
    else:
        flash('Account created, but the email could not be sent. Use "Resend activation link" later.', 'warning')
    return redirect(url_for('admin_users.index'))


@admin_users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def edit(user_id):
    target = get_target(user_id)
    if request.method == 'GET':
        form = {'first_name': target.first_name, 'middle_name': target.middle_name or '',
                'last_name': target.last_name, 'email': target.email}
        return render_template('admin/user_form.html', mode='edit', target=target, form=form)

    f = request.form
    first = clean_name(f.get('first_name', ''))
    middle = clean_name(f.get('middle_name', ''))
    last = clean_name(f.get('last_name', ''))
    email = f.get('email', '').strip().lower()

    errors = person_errors(first, middle, last, email)
    other = User.find_by_email(email) if EMAIL_RE.match(email) else None
    if other and other.id != target.id:
        errors.append('That email already belongs to another account.')
    if errors:
        for message in errors:
            flash(message, 'danger')
        return render_template('admin/user_form.html', mode='edit', target=target, form=f)

    target.update_details(first, middle or None, last, email)
    AuditLog.record('Account updated', email)
    flash('Account updated.', 'success')
    return redirect(url_for('admin_users.index'))


@admin_users_bp.route('/<int:user_id>/toggle', methods=['POST'])
@roles_required('admin')
def toggle(user_id):
    target = get_target(user_id)
    new_state = not target.is_active
    target.set_active(new_state)
    AuditLog.record('Account activated' if new_state else 'Account deactivated', target.email)
    flash(f'{target.full_name} is now {"active" if new_state else "deactivated"}.', 'success')
    return redirect(url_for('admin_users.index'))


@admin_users_bp.route('/<int:user_id>/force-logout', methods=['POST'])
@roles_required('admin')
def force_logout(user_id):
    target = get_target(user_id)
    target.force_logout()
    AuditLog.record('Forced logout', target.email)
    flash(f'{target.full_name} was logged out of all devices.', 'success')
    return redirect(url_for('admin_users.index'))


@admin_users_bp.route('/<int:user_id>/unlock', methods=['POST'])
@roles_required('admin')
def unlock(user_id):
    target = get_target(user_id)
    target.unlock()
    AuditLog.record('Account unlocked', target.email)
    flash(f'{target.full_name} can log in again.', 'success')
    return redirect(url_for('admin_users.index'))


@admin_users_bp.route('/<int:user_id>/resend', methods=['POST'])
@roles_required('admin')
def resend(user_id):
    target = get_target(user_id)
    if target.is_activated:
        flash('That account is already activated.', 'info')
    elif send_activation(target):
        AuditLog.record('Activation link resent', target.email)
        flash(f'Activation link sent to {target.email}.', 'success')
    else:
        flash('The email could not be sent. Please try again.', 'danger')
    return redirect(url_for('admin_users.index'))


@admin_users_bp.route('/<int:user_id>/reset', methods=['POST'])
@roles_required('admin')
def reset(user_id):
    target = get_target(user_id)
    link = url_for('auth.reset', token=target.get_reset_token(), _external=True)
    if send_email('Reset your SIT-EnrollEase password', target.email, 'reset', user=target, link=link):
        AuditLog.record('Password reset link sent', target.email)
        flash(f'Reset link sent to {target.email}.', 'success')
    else:
        flash('The email could not be sent. Please try again.', 'danger')
    return redirect(url_for('admin_users.index'))