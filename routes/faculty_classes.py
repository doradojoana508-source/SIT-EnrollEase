from datetime import date
from flask import (Blueprint, render_template, request, redirect, url_for, flash, abort, g,
                   send_from_directory)
from models.audit_log import AuditLog
from models.class_offering import ClassOffering
from models.grade import Grade
from models.lms_material import LmsMaterial
from models.class_announcement import ClassAnnouncement
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
    year_level = request.args.get('year', '')
    if year_level not in Teaching.YEAR_LEVELS:
        year_level = ''
    rows = Teaching.classes(g.user.id, term['id'], year_level or None) if term else []
    return render_template('faculty/classes.html', terms=terms, term=term, rows=rows, year_level=year_level,
                           year_levels=Teaching.YEAR_LEVELS)


def _page(class_id, meeting_date=None):
    c = _mine(class_id)
    term = Teaching.term(c['term_id'])
    full_roster = Teaching.roster(c, term)
    year_level = request.args.get('year', '')
    if year_level not in Teaching.YEAR_LEVELS:
        year_level = ''
    roster = [r for r in full_roster if not year_level or r['year_level'] == year_level]
    meeting_date = meeting_date or Teaching.parse_date(request.args.get('date')) or date.today()
    return render_template('faculty/class.html', c=c, term=term, roster=roster, grades=Grade.GRADES,
                           statuses=Teaching.STATUSES, meeting_date=meeting_date, today=date.today(),
                           marked=Teaching.day(class_id, meeting_date), summary=Teaching.summary(class_id),
                           dates=Teaching.dates(class_id), materials=LmsMaterial.for_class(class_id),
                           class_announcements=ClassAnnouncement.for_class(class_id),
                           allowed=LmsMaterial.ALLOWED_TEXT, max_mb=LmsMaterial.MAX_BYTES // (1024 * 1024),
                           year_level=year_level, year_levels=Teaching.YEAR_LEVELS)


@faculty_classes_bp.route('/uploads')
@roles_required('faculty')
def uploads():
    terms = ClassOffering.terms()
    term = ClassOffering.pick_term(terms, request.args.get('term', type=int))
    rows = Teaching.classes(g.user.id, term['id']) if term else []
    return render_template('faculty/uploads.html', terms=terms, term=term, rows=rows)


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


@faculty_classes_bp.route('/<int:class_id>/announcements', methods=['POST'])
@roles_required('faculty')
def add_announcement(class_id):
    c = _mine(class_id)
    _ident, errors = ClassAnnouncement.create(class_id, request.form.get('title'), request.form.get('body'), g.user.id)
    if errors:
        for error in errors:
            flash(error, 'danger')
    else:
        title = ' '.join(request.form.get('title', '').split())
        AuditLog.record('Class announcement posted', f"{c['code']}: {title}"[:200])
        flash('Announcement posted to this class.', 'success')
    return redirect(url_for('faculty_classes.view', class_id=class_id) + '#class-announcements')


@faculty_classes_bp.route('/<int:class_id>/announcements/<int:announcement_id>/delete', methods=['POST'])
@roles_required('faculty')
def delete_announcement(class_id, announcement_id):
    c = _mine(class_id)
    ClassAnnouncement.delete(class_id, announcement_id)
    AuditLog.record('Class announcement deleted', f"{c['code']} announcement #{announcement_id}")
    flash('Announcement removed from this class.', 'success')
    return redirect(url_for('faculty_classes.view', class_id=class_id) + '#class-announcements')


# ---------------- Materials (e-books, handouts, links) ----------------
def _material(class_id, material_id):
    _mine(class_id)
    row = LmsMaterial.find(material_id)
    if row is None or row['class_id'] != class_id:
        abort(404)
    return row


@faculty_classes_bp.route('/<int:class_id>/materials', methods=['POST'])
@roles_required('faculty')
def add_material(class_id):
    c = _mine(class_id)
    material_id, errors = LmsMaterial.add(class_id, request.form, request.files.get('file'), g.user)
    if errors:
        for e in errors:
            flash(e, 'danger')
        return redirect(url_for('faculty_classes.view', class_id=class_id) + '#materials')
    title = ' '.join(request.form.get('title', '').split())
    AuditLog.record('Material added', f"{c['code']}: {title}"[:200])
    message = 'Material added.'
    if request.form.get('is_visible') == '1' and request.form.get('notify') == '1':
        total = LmsMaterial.notify_students(class_id, c['code'], title)
        message = f'Material added. {total} student(s) were notified.'
    elif request.form.get('is_visible') != '1':
        message = 'Material saved as hidden. Students cannot see it until you show it.'
    flash(message, 'success')
    return redirect(url_for('faculty_classes.view', class_id=class_id) + '#materials')


@faculty_classes_bp.route('/<int:class_id>/materials/<int:material_id>/edit', methods=['GET', 'POST'])
@roles_required('faculty')
def edit_material(class_id, material_id):
    c = _mine(class_id)
    row = _material(class_id, material_id)
    if request.method == 'POST':
        errors = LmsMaterial.update(row, request.form, request.files.get('file'))
        if not errors:
            AuditLog.record('Material updated', f"{c['code']}: {row['title']}"[:200])
            flash('Material updated.', 'success')
            return redirect(url_for('faculty_classes.view', class_id=class_id) + '#materials')
        return render_template('faculty/material_edit.html', c=c, m=row, values=request.form, errors=errors,
                               allowed=LmsMaterial.ALLOWED_TEXT, max_mb=LmsMaterial.MAX_BYTES // (1024 * 1024))
    values = {'title': row['title'], 'description': row['description'] or '', 'link_url': row['link_url'] or '',
              'phase': row.get('phase', 'PRELIM'), 'is_visible': '1' if row['is_visible'] else ''}
    return render_template('faculty/material_edit.html', c=c, m=row, values=values, errors=[],
                           allowed=LmsMaterial.ALLOWED_TEXT, max_mb=LmsMaterial.MAX_BYTES // (1024 * 1024))


@faculty_classes_bp.route('/<int:class_id>/materials/<int:material_id>/toggle', methods=['POST'])
@roles_required('faculty')
def toggle_material(class_id, material_id):
    c = _mine(class_id)
    row = _material(class_id, material_id)
    LmsMaterial.set_visible(material_id, not row['is_visible'])
    AuditLog.record('Material shown' if not row['is_visible'] else 'Material hidden', f"{c['code']}: {row['title']}"[:200])
    flash('Material is now visible to students.' if not row['is_visible'] else 'Material is now hidden from students.',
          'success')
    return redirect(url_for('faculty_classes.view', class_id=class_id) + '#materials')


@faculty_classes_bp.route('/<int:class_id>/materials/<int:material_id>/delete', methods=['POST'])
@roles_required('faculty')
def delete_material(class_id, material_id):
    c = _mine(class_id)
    row = _material(class_id, material_id)
    LmsMaterial.delete(material_id)
    AuditLog.record('Material deleted', f"{c['code']}: {row['title']}"[:200])
    flash('Material deleted.', 'success')
    return redirect(url_for('faculty_classes.view', class_id=class_id) + '#materials')


@faculty_classes_bp.route('/<int:class_id>/materials/<int:material_id>/file')
@roles_required('faculty')
def material_file(class_id, material_id):
    row = _material(class_id, material_id)
    if row['kind'] != 'File':
        abort(404)
    response = send_from_directory(LmsMaterial.folder(class_id), row['stored_name'], mimetype=row['mime_type'],
                                   download_name=row['original_name'], as_attachment=not row['inline'])
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response