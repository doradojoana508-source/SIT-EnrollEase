from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models.notification import Notification
from models.student_record import StudentRecord
from utils import roles_required

portal_student_bp = Blueprint('portal_student', __name__, url_prefix='/portal')


@portal_student_bp.route('/cor')
@roles_required('student')
def cor():
    rows, view = StudentRecord.cor_view(g.user, request.args.get('term', type=int))
    return render_template('portal/cor.html', rows=rows, v=view)


@portal_student_bp.route('/cor/print')
@roles_required('student')
def cor_print():
    rows, view = StudentRecord.cor_view(g.user, request.args.get('term', type=int))
    if view is None:
        return redirect(url_for('portal_student.cor'))
    return render_template('print/cor.html', v=view, back=url_for('portal_student.cor', term=view['term_id']))


@portal_student_bp.route('/tuition')
@roles_required('student')
def tuition():
    return render_template('portal/tuition.html', t=StudentRecord.tuition(g.user.id))


@portal_student_bp.route('/notices/read', methods=['POST'])
@roles_required('student')
def read_notices():
    Notification.mark_all_read(g.user.id)
    flash('Notices marked as read.', 'success')
    return redirect(url_for('portal.dashboard'))