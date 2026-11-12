from flask import Blueprint, render_template, abort, send_from_directory, g
from models.lms_material import LmsMaterial
from models.class_announcement import ClassAnnouncement
from utils import roles_required

portal_library_bp = Blueprint('portal_library', __name__, url_prefix='/portal/library')


def _student_class_context():
    terms = LmsMaterial.for_student(g.user.id)
    announcements = ClassAnnouncement.for_student(g.user.id)
    class_rows = ClassAnnouncement.classes_for_student(g.user.id)
    by_term = {t['label']: t for t in terms}
    for first in class_rows:
        class_id = first['class_id']
        label = f"{('1st' if first['term_no'] == 1 else '2nd' if first['term_no'] == 2 else '3rd')} Trimester, {first['academic_year']}"
        term = by_term.get(label)
        if term is None:
            term = {'label': label, 'classes': []}
            terms.append(term)
            by_term[label] = term
        existing = next(
    (c for c in term['classes']
     if c.get('class_id', c.get('id')) == class_id),
    None
)
        if existing is None:
            term['classes'].append({'class_id': class_id, 'code': first['code'],
                                    'title': first['class_title'], 'materials': []})
    return terms, announcements


@portal_library_bp.route('/')
@roles_required('student')
def index():
    terms, announcements = _student_class_context()
    return render_template('portal/library.html', terms=terms, announcements=announcements, page_title='Library')


@portal_library_bp.route('/classes')
@roles_required('student')
def classes():
    terms, announcements = _student_class_context()
    return render_template('portal/library.html', terms=terms, announcements=announcements, page_title='Classes')


@portal_library_bp.route('/file/<int:material_id>')
@roles_required('student')
def file(material_id):
    row = LmsMaterial.student_find(material_id, g.user.id)
    if row is None or row['kind'] != 'File':
        abort(404)
    response = send_from_directory(LmsMaterial.folder(row['class_id']), row['stored_name'], mimetype=row['mime_type'],
                                   download_name=row['original_name'], as_attachment=not row['inline'])
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response