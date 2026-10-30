from datetime import date, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for, flash, g, abort,
                   send_from_directory)
from models.application import Application
from models.application_document import ApplicationDocument
from models.notification import Notification
from utils import roles_required
from routes.auth import NAME_RE, clean_name

applicant_bp = Blueprint('applicant', __name__, url_prefix='/applicant')


def my_application():
    return Application.find_by_user(g.user.id)


def doc_row(type_id):
    """Ang application ng naka-login na user at ang isang dokumento nito. 404 kung hindi sa kanya."""
    application = my_application()
    if application is None:
        abort(404)
    row = next((r for r in application.document_rows() if r['id'] == type_id), None)
    if row is None:
        abort(404)
    return application, row


@applicant_bp.route('/dashboard')
@roles_required('applicant')
def dashboard():
    application = my_application()
    ctx = dict(application=application, steps=Application.STATUS_STEPS, notices=Notification.unread_for(g.user.id),
               program=None, interview=None, doc_done=0, doc_total=0, problems=[], bring=[], rejected=[])
    if application:
        if application.program_id:
            ctx['program'] = dict(Application.program_options()).get(application.program_id)
        needed = [r for r in application.document_rows() if not r['online']]
        ctx.update(doc_total=len(needed), doc_done=len([r for r in needed if r['upload']]),
                   bring=[r['name'] for r in needed],
                   rejected=[r for r in needed if r['upload'] and r['upload']['status'] == 'Rejected'],
                   interview=application.current_interview())
        if application.is_editable:
            ctx['problems'] = application.readiness()
    return render_template('applicant/dashboard.html', **ctx)


@applicant_bp.route('/application', methods=['GET', 'POST'])
@roles_required('applicant')
def application():
    current = my_application()
    if current and not current.is_editable:
        flash('Your application is already submitted and can no longer be edited.', 'info')
        return redirect(url_for('applicant.dashboard'))

    options = Application.program_options()
    page = dict(options=options, choices=Application.CHOICES,
                max_birth=(date.today() - timedelta(days=365 * 10)).isoformat(), year=date.today().year)

    if request.method == 'POST':
        first = clean_name(request.form.get('first_name', ''))
        middle = clean_name(request.form.get('middle_name', ''))
        last = clean_name(request.form.get('last_name', ''))
        data, errors = Application.clean(request.form, {pid for pid, _ in options})

        if not (2 <= len(first) <= 50 and NAME_RE.match(first)):
            errors.append('Given name must be 2 to 50 letters.')
        if middle and not (len(middle) <= 50 and NAME_RE.match(middle)):
            errors.append('Middle name may only contain letters, up to 50 characters.')
        if not (2 <= len(last) <= 50 and NAME_RE.match(last)):
            errors.append('Surname must be 2 to 50 letters.')

        if errors:
            for message in errors:
                flash(message, 'danger')
            return render_template('applicant/application_form.html', form=request.form, **page)

        g.user.update_details(first, middle or None, last, g.user.email)   # ina-update ang pangalan ng account

        current = current or Application()
        current.user_id = g.user.id
        for name, value in data.items():
            setattr(current, name, value)
        current.save()
        flash('Draft saved.', 'success')
        return redirect(url_for('applicant.dashboard'))

    form = current.to_form() if current else {}
    return render_template('applicant/application_form.html', form=form, **page)


# ---------------- Mga dokumento (CRUD) ----------------
@applicant_bp.route('/documents')
@roles_required('applicant')
def documents():
    current = my_application()
    if not current or not current.program_id:
        flash('Fill in your application form and choose a program first.', 'info')
        return redirect(url_for('applicant.application'))
    return render_template('applicant/documents.html', application=current, rows=current.document_rows(),
                           problems=current.readiness() if current.is_editable else [],
                           max_mb=ApplicationDocument.MAX_BYTES // (1024 * 1024))


@applicant_bp.route('/documents/<int:type_id>/upload', methods=['POST'])
@roles_required('applicant')
def document_upload(type_id):
    current, row = doc_row(type_id)
    if not row['can_change']:
        flash('This document can no longer be changed.', 'warning')
    else:
        ok, message = ApplicationDocument.store(current.id, type_id, request.files.get('file'))
        flash(message, 'success' if ok else 'danger')
    return redirect(url_for('applicant.documents'))


@applicant_bp.route('/documents/<int:type_id>/delete', methods=['POST'])
@roles_required('applicant')
def document_delete(type_id):
    current, row = doc_row(type_id)
    if not row['can_delete']:
        flash('This document can no longer be deleted.', 'warning')
    else:
        ApplicationDocument.remove(current.id, type_id)
        flash('File deleted.', 'success')
    return redirect(url_for('applicant.documents'))


@applicant_bp.route('/documents/<int:type_id>/file')
@roles_required('applicant')
def document_file(type_id):
    """Binubuksan lang ng may-ari. Hindi ito nasa /static, kaya hindi puwedeng hulaan ang link."""
    current, row = doc_row(type_id)
    upload = row['upload']
    if not upload:
        abort(404)
    response = send_from_directory(ApplicationDocument.folder(current.id), upload['stored_name'],
                                   mimetype=upload['mime_type'], download_name=upload['original_name'])
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


# ---------------- Submit, Withdraw, Notices ----------------
@applicant_bp.route('/submit', methods=['POST'])
@roles_required('applicant')
def submit():
    current = my_application()
    if current is None:
        abort(404)
    if not request.form.get('certify'):
        flash('Please certify that the information you gave is true.', 'danger')
        return redirect(url_for('applicant.dashboard'))
    try:
        current.submit(request.form.get('signature', ''))
        flash('Application submitted! We will notify you here and by email once there is an update.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('applicant.dashboard'))


@applicant_bp.route('/withdraw', methods=['POST'])
@roles_required('applicant')
def withdraw():
    current = my_application()
    if current is None:
        abort(404)
    try:
        current.withdraw()
        flash('Your application has been withdrawn.', 'info')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('applicant.dashboard'))


@applicant_bp.route('/notices/<int:notice_id>/read', methods=['POST'])
@roles_required('applicant')
def notice_read(notice_id):
    Notification.mark_read(notice_id, g.user.id)
    return redirect(url_for('applicant.dashboard'))