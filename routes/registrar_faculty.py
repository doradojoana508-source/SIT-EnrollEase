from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models.audit_log import AuditLog
from models.faculty import Faculty
from utils import roles_required

registrar_faculty_bp = Blueprint('registrar_faculty', __name__, url_prefix='/registrar/faculty')


@registrar_faculty_bp.route('/')
@roles_required('registrar')
def index():
    return render_template('registrar/faculty.html', faculty=Faculty.all())


@registrar_faculty_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@roles_required('registrar')
def edit(user_id):
    person = Faculty.find(user_id)
    if person is None:
        abort(404)
    errors = []
    if request.method == 'POST':
        data, errors = Faculty.clean(request.form)
        if not errors:
            Faculty.save(user_id, data)
            AuditLog.record('Faculty profile updated', person['email'])
            flash('Profile saved.', 'success')
            return redirect(url_for('registrar_faculty.index'))
        values = request.form
    else:
        values = {'title': person['title'] or '', 'display_name': person['display_name'] or '',
                  'specialties': person['specialties'] or ''}
    return render_template('registrar/faculty_form.html', person=person, values=values, errors=errors,
                           titles=Faculty.TITLES)