from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g, send_from_directory
from models.university_resource import UniversityResource
from models.lms_material import LmsMaterial
from models.audit_log import AuditLog
from utils import roles_required

university_resources_bp = Blueprint('university_resources', __name__, url_prefix='/portal/resources')


@university_resources_bp.route('/')
@roles_required('student')
def index():
    return render_template('portal/resources.html', groups=UniversityResource.active(), page_title='Resources')


@university_resources_bp.route('/manage')
@roles_required('admin', 'registrar')
def manage():
    return render_template('resources/manage.html', rows=UniversityResource.all(),
                           allowed=LmsMaterial.ALLOWED_TEXT, max_mb=LmsMaterial.MAX_BYTES // (1024 * 1024))


@university_resources_bp.route('/upload', methods=['POST'])
@roles_required('admin', 'registrar')
def upload():
    ident, errors = UniversityResource.add(request.form, request.files.get('file'), g.user.id)
    if errors:
        for error in errors:
            flash(error, 'danger')
    else:
        AuditLog.record('University resource uploaded', f"Resource #{ident}: {request.form.get('title', '')}"[:250])
        flash('University resource added.', 'success')
    return redirect(url_for('university_resources.manage'))


@university_resources_bp.route('/<int:resource_id>/toggle', methods=['POST'])
@roles_required('admin', 'registrar')
def toggle(resource_id):
    row = UniversityResource.find(resource_id)
    if row is None:
        abort(404)
    UniversityResource.set_active(resource_id, not row['is_active'])
    AuditLog.record('University resource visibility changed', f"Resource #{resource_id}")
    flash('Resource visibility updated.', 'success')
    return redirect(url_for('university_resources.manage'))


@university_resources_bp.route('/<int:resource_id>/delete', methods=['POST'])
@roles_required('admin', 'registrar')
def delete(resource_id):
    row = UniversityResource.find(resource_id)
    if row is None:
        abort(404)
    UniversityResource.delete(resource_id)
    AuditLog.record('University resource deleted', f"Resource #{resource_id}: {row['title']}")
    flash('Resource removed.', 'success')
    return redirect(url_for('university_resources.manage'))


@university_resources_bp.route('/<int:resource_id>/file')
def file(resource_id):
    if g.user is None:
        abort(403)
    row = UniversityResource.find(resource_id) if g.user.role in ('admin', 'registrar') else UniversityResource.student_find(resource_id) if g.user.role == 'student' else None
    if row is None or row['kind'] != 'File':
        abort(404)
    response = send_from_directory(UniversityResource.folder(), row['stored_name'], mimetype=row['mime_type'],
                                   download_name=row['original_name'], as_attachment=True)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response
