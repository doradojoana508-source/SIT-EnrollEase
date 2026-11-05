from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from db import query
from models.audit_log import AuditLog
from models.class_offering import ClassOffering
from models.grade import Grade
from models.registrar_record import RegistrarRecord
from models.transcript import Transcript
from utils import roles_required, Pager

registrar_records_bp = Blueprint('registrar_records', __name__, url_prefix='/registrar/records')


def _record(user_id):
    rec = RegistrarRecord.find(user_id)
    if rec is None:
        abort(404)
    return rec


def _grade_context():
    return dict(grades=Grade.GRADES, terms=Grade.TERM_NAMES, options=ClassOffering.subject_options())


def _page(user_id, values=None, errors=None):
    rec = _record(user_id)
    if values is None:
        current = query("SELECT academic_year FROM academic_terms WHERE is_current = 1 LIMIT 1", one=True)
        values = {'academic_year': current['academic_year'] if current else ''}
    return render_template('registrar/record.html', r=rec, groups=Grade.grouped(Grade.for_student(user_id)),
                           cors=RegistrarRecord.cors(user_id), tor=RegistrarRecord.tor_info(user_id),
                           values=values, errors=errors or [], **_grade_context())


@registrar_records_bp.route('/')
@roles_required('registrar')
def index():
    q = request.args.get('q', '').strip()[:80]
    program_id = request.args.get('program', type=int)
    pager = Pager(RegistrarRecord.count(q, program_id), request.args.get('page', 1, type=int))
    rows = RegistrarRecord.rows(q, program_id, pager.per_page, (pager.page - 1) * pager.per_page)
    return render_template('registrar/records.html', rows=rows, pager=pager, q=q, program_id=program_id,
                           programs=RegistrarRecord.programs())


@registrar_records_bp.route('/<int:user_id>')
@roles_required('registrar')
def view(user_id):
    return _page(user_id)


@registrar_records_bp.route('/<int:user_id>/grades/add', methods=['POST'])
@roles_required('registrar')
def grade_add(user_id):
    rec = _record(user_id)
    data, errors = Grade.clean(request.form, user_id)
    if errors:
        return _page(user_id, request.form, errors)
    Grade.create(user_id, data, g.user)
    AuditLog.record('Grade added', f"{rec['student_id']}: {data['code']} {data['grade']}")
    flash('Grade saved.', 'success')
    return redirect(url_for('registrar_records.view', user_id=user_id) + '#grades')


@registrar_records_bp.route('/<int:user_id>/grades/<int:grade_id>/edit', methods=['GET', 'POST'])
@roles_required('registrar')
def grade_edit(user_id, grade_id):
    rec = _record(user_id)
    existing = Grade.find(grade_id, user_id)
    if existing is None:
        abort(404)
    errors = []
    if request.method == 'POST':
        data, errors = Grade.clean(request.form, user_id, existing)
        if not errors:
            Grade.update(grade_id, data, g.user)
            AuditLog.record('Grade updated', f"{rec['student_id']}: {data['code']} {data['grade']}")
            flash('Grade updated.', 'success')
            return redirect(url_for('registrar_records.view', user_id=user_id) + '#grades')
        values = request.form
    else:
        values = Grade.to_form(existing)
    return render_template('registrar/grade_form.html', r=rec, values=values, errors=errors, existing=existing,
                           **_grade_context())


@registrar_records_bp.route('/<int:user_id>/grades/<int:grade_id>/delete', methods=['POST'])
@roles_required('registrar')
def grade_delete(user_id, grade_id):
    rec = _record(user_id)
    existing = Grade.find(grade_id, user_id)
    if existing is None:
        abort(404)
    Grade.delete(grade_id)
    AuditLog.record('Grade deleted', f"{rec['student_id']}: {existing['code']}")
    flash('Grade deleted.', 'success')
    return redirect(url_for('registrar_records.view', user_id=user_id) + '#grades')


@registrar_records_bp.route('/<int:user_id>/tor-info', methods=['POST'])
@roles_required('registrar')
def tor_info(user_id):
    rec = _record(user_id)
    RegistrarRecord.save_tor_info(user_id, request.form)
    AuditLog.record('TOR details saved', rec['student_id'])
    flash('TOR details saved.', 'success')
    return redirect(url_for('registrar_records.view', user_id=user_id) + '#tor')


@registrar_records_bp.route('/<int:user_id>/grade-report')
@roles_required('registrar')
def grade_report(user_id):
    report = Transcript.grade_report(user_id, request.args.get('ay', ''), request.args.get('tn', 0, type=int))
    if report is None:
        abort(404)
    return render_template('print/grade_report.html', v=report, back=url_for('registrar_records.view', user_id=user_id))


@registrar_records_bp.route('/<int:user_id>/tor')
@roles_required('registrar')
def tor(user_id):
    data = Transcript.tor(user_id)
    if data is None:
        abort(404)
    AuditLog.record('TOR printed', _record(user_id)['student_id'])
    return render_template('print/tor.html', v=data, back=url_for('registrar_records.view', user_id=user_id))