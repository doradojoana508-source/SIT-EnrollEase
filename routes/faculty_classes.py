from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from models.audit_log import AuditLog
from models.class_offering import ClassOffering
from models.grade import Grade
from models.teaching import Teaching
from utils import roles_required

faculty_classes_bp = Blueprint('faculty_classes', __name__, url_prefix='/faculty/classes')


def _mine(class_id):
    row = Teaching.mine(class_id, g.user.id)
    if row is None:
        abort(404)                                    # hindi sa kanya ang klase
    return row


@faculty_classes_bp.route('/')
@roles_required('faculty')
def index():
    terms = ClassOffering.terms()
    term = ClassOffering.pick_term(terms, request.args.get('term', type=int))
    rows = Teaching.classes(g.user.id, term['id']) if term else []
    return render_template('faculty/classes.html', terms=terms, term=term, rows=rows)


def _page(class_id, meeting_date=None):
    c = _mine(class_id)
    term = Teaching.term(c['term_id'])
    roster = Teaching.roster(c, term)
    meeting_date = meeting_date or Teaching.parse_date(request.args.get('date')) or date.today()
    return render_template('faculty/class.html', c=c, term=term, roster=roster, grades=Grade.GRADES,
                           statuses=Teaching.STATUSES, meeting_date=meeting_date, today=date.today(),
                           marked=Teaching.day(class_id, meeting_date), summary=Teaching.summary(class_id),
                           dates=Teaching.dates(class_id))


@faculty_classes_bp.route('/<int:class_id>')
@roles_required('faculty')
def view(class_id):
    return _page(class_id)


@faculty_classes_bp.route('/<int:class_id>/grades', methods=['POST'])
@roles_required('faculty')
def save_grades(class_id):
    c = _mine(class_id)
    term = Teaching.term(c['term_id'])
    saved, errors = Teaching.save_grades(c, term, Teaching.roster(c, term), request.form, g.user)
    if saved:
        AuditLog.record('Grades encoded', f"{c['code']}: {saved} grade(s)")
        flash(f'{saved} grade(s) saved. The students were notified.', 'success')
    for e in errors:
        flash(e, 'danger')
    if not saved and not errors:
        flash('No changes to save.', 'info')
    return redirect(url_for('faculty_classes.view', class_id=class_id) + '#grades')


@faculty_classes_bp.route('/<int:class_id>/attendance', methods=['POST'])
@roles_required('faculty')
def save_attendance(class_id):
    c = _mine(class_id)
    meeting_date = Teaching.parse_date(request.form.get('date'))
    if meeting_date is None:
        flash('Choose a valid class date (not in the future).', 'danger')
        return redirect(url_for('faculty_classes.view', class_id=class_id) + '#attendance')
    term = Teaching.term(c['term_id'])
    saved = Teaching.save_day(class_id, meeting_date, Teaching.roster(c, term), request.form, g.user)
    AuditLog.record('Attendance recorded', f"{c['code']} {meeting_date.isoformat()}: {saved} student(s)")
    flash(f'Attendance saved for {meeting_date:%B} {meeting_date.day}, {meeting_date:%Y}.', 'success')
    return redirect(url_for('faculty_classes.view', class_id=class_id, date=meeting_date.isoformat()) + '#attendance')