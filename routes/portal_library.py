from flask import Blueprint, render_template, abort, send_from_directory, g
from models.lms_material import LmsMaterial
from utils import roles_required

portal_library_bp = Blueprint('portal_library', __name__, url_prefix='/portal/library')


@portal_library_bp.route('/')
@roles_required('student')
def index():
    return render_template('portal/library.html', terms=LmsMaterial.for_student(g.user.id))


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