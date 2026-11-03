from flask import Blueprint, render_template, redirect, url_for, flash
from models.audit_log import AuditLog
from models.pending_student import PendingStudent
from models.user import User
from routes.admin_users import STUDENT_ID_RE, send_activation
from utils import roles_required

admin_pending_bp = Blueprint('admin_pending', __name__, url_prefix='/admin/pending-students')


def _create(row):
    """Ginagawang Student account ang applicant. Ibinabalik ang (ok, mensahe)."""
    name = f"{row['first_name']} {row['last_name']}"
    if not STUDENT_ID_RE.match(row['student_id'] or ''):
        return False, f'{name}: the Student ID is invalid.'
    if User.find_by_username(row['student_id']):
        return False, f"{name}: Student ID {row['student_id']} is already used."
    if not row['birthdate']:
        return False, f'{name}: the application has no birth date.'
    user = User.find(row['user_id'])
    if user is None or user.role != 'applicant':
        return False, f'{name} already has a student account.'
    user.promote_to_student(row['student_id'], row['birthdate'].strftime('%y/%m/%d'))
    user = User.find(row['user_id'])
    AuditLog.record('Applicant promoted to student', f"{user.email} -> {row['student_id']}")
    if send_activation(user):
        return True, f"{name}: account created and activation link sent to {user.email}."
    return True, f"{name}: account created, but the email could not be sent. Use Resend activation link under Users."


@admin_pending_bp.route('/')
@roles_required('admin')
def index():
    return render_template('admin/pending_students.html', rows=PendingStudent.all())


@admin_pending_bp.route('/<int:user_id>/create', methods=['POST'])
@roles_required('admin')
def create(user_id):
    row = PendingStudent.find(user_id)
    if row is None:
        flash('That student is no longer pending.', 'info')
    else:
        ok, message = _create(row)
        flash(message, 'success' if ok else 'danger')
    return redirect(url_for('admin_pending.index'))


@admin_pending_bp.route('/create-all', methods=['POST'])
@roles_required('admin')
def create_all():
    made = 0
    for row in PendingStudent.all():
        ok, message = _create(row)
        made += ok
        if not ok:
            flash(message, 'danger')
    flash(f'{made} student account(s) created.', 'success' if made else 'info')
    return redirect(url_for('admin_pending.index'))