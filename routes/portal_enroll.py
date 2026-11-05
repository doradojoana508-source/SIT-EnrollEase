from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models.audit_log import AuditLog
from models.preenrollment import PreEnrollment
from utils import roles_required

portal_enroll_bp = Blueprint('portal_enroll', __name__, url_prefix='/portal/enroll')


@portal_enroll_bp.route('/')
@roles_required('student')
def index():
    info = PreEnrollment.summary(g.user.id)
    programs = PreEnrollment.programs() if info['needs_program'] else []
    return render_template('portal/enroll.html', info=info, programs=programs, types=PreEnrollment.TYPES)


@portal_enroll_bp.route('/submit', methods=['POST'])
@roles_required('student')
def submit():
    try:
        term = PreEnrollment.create(g.user, request.form.get('student_type', ''), request.form.get('program_id', type=int))
        AuditLog.record('Pre-enrollment submitted', f"{g.user.username}: {term['label']}")
        flash('Pre-enrollment received. The Finance office will prepare your quotation.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('portal_enroll.index'))


@portal_enroll_bp.route('/cancel', methods=['POST'])
@roles_required('student')
def cancel():
    try:
        PreEnrollment.cancel(g.user)
        AuditLog.record('Pre-enrollment cancelled', g.user.username or '')
        flash('Pre-enrollment cancelled.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('portal_enroll.index'))