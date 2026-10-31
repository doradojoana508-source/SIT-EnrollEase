from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_from_directory, g
from models.application import Application
from models.application_document import ApplicationDocument
from models.audit_log import AuditLog
from models.notification import Notification
from models.user import User
from utils import roles_required, Pager

registrar_applications_bp = Blueprint('registrar_applications', __name__, url_prefix='/registrar/applications')

STATUS_FILTERS = ('Submitted', 'Approved', 'Interview Scheduled', 'For Enrollment', 'Enrolled', 'Rejected')
PER_PAGE = 10


def get_application(application_id):
    """Hindi nakikita ng Registrar ang Draft."""
    application = Application.find(application_id)
    if application is None or application.status == 'Draft':
        abort(404)
    return application


def get_doc_row(application, type_id):
    row = next((r for r in application.document_rows() if r['id'] == type_id), None)
    if row is None:
        abort(404)
    return row


@registrar_applications_bp.route('/')
@roles_required('registrar')
def index():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    if status not in STATUS_FILTERS:
        status = ''
    page = request.args.get('page', 1, type=int)
    rows, total = Application.search(q, status, PER_PAGE, (max(page, 1) - 1) * PER_PAGE)
    pager = Pager(total, page, PER_PAGE)
    return render_template('registrar/applications.html', rows=rows, pager=pager, q=q, status=status,
                           statuses=STATUS_FILTERS, programs=dict(Application.program_options()))


@registrar_applications_bp.route('/<int:application_id>')
@roles_required('registrar')
def review(application_id):
    application = get_application(application_id)
    return render_template('registrar/review.html', application=application,
                           owner=User.find(application.user_id),
                           program=dict(Application.program_options()).get(application.program_id),
                           rows=application.document_rows(),
                           interview=application.current_interview(),
                           can_review=application.status == 'Submitted')


@registrar_applications_bp.route('/<int:application_id>/documents/<int:type_id>/file')
@roles_required('registrar')
def document_file(application_id, type_id):
    application = get_application(application_id)
    upload = get_doc_row(application, type_id)['upload']
    if not upload:
        abort(404)
    response = send_from_directory(ApplicationDocument.folder(application.id), upload['stored_name'],
                                   mimetype=upload['mime_type'], download_name=upload['original_name'])
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@registrar_applications_bp.route('/<int:application_id>/documents/<int:type_id>/verify', methods=['POST'])
@roles_required('registrar')
def verify_document(application_id, type_id):
    application = get_application(application_id)
    row = get_doc_row(application, type_id)
    if application.status != 'Submitted' or not row['upload']:
        flash('This document cannot be verified right now.', 'warning')
    else:
        ApplicationDocument.set_status(application.id, type_id, 'Verified')
        AuditLog.record('Document verified', f'Application #{application.id}: {row["name"]}')
        flash(f'{row["name"]} verified.', 'success')
    return redirect(url_for('registrar_applications.review', application_id=application.id))


@registrar_applications_bp.route('/<int:application_id>/documents/<int:type_id>/reject', methods=['POST'])
@roles_required('registrar')
def reject_document(application_id, type_id):
    application = get_application(application_id)
    row = get_doc_row(application, type_id)
    remarks = ' '.join(request.form.get('remarks', '').split())

    if application.status != 'Submitted' or not row['upload']:
        flash('This document cannot be rejected right now.', 'warning')
    elif not 3 <= len(remarks) <= 255:
        flash('Give the applicant a short reason (3 to 255 characters).', 'danger')
    else:
        ApplicationDocument.set_status(application.id, type_id, 'Rejected', remarks)
        AuditLog.record('Document rejected', f'Application #{application.id}: {row["name"]}')
        Notification.notify(
            User.find(application.user_id), 'Action needed: replace a document', 'Document needs to be replaced',
            f'Your {row["name"]} was not accepted. Please upload a new file.',
            [('Document', row['name']), ('Reason', remarks)])
        flash(f'{row["name"]} rejected. The applicant was notified.', 'success')
    return redirect(url_for('registrar_applications.review', application_id=application.id))

@registrar_applications_bp.route('/<int:application_id>/print')
@roles_required('registrar')
def print_form(application_id):
    application = get_application(application_id)
    photo_id = application.photo_type_id()
    return render_template('print/admission_form.html', application=application,
                           owner=User.find(application.user_id),
                           program=dict(Application.program_options()).get(application.program_id),
                           photo_url=url_for('registrar_applications.document_file', application_id=application.id,
                                             type_id=photo_id) if photo_id else None,
                           back=url_for('registrar_applications.review', application_id=application.id))



# ---------------- Desisyon: approve, interview, reject ----------------
def interview_from_form(form):
    """Binabasa ang schedule mula sa form. Ibinabalik ang dict, o ValueError kung mali."""
    try:
        when = datetime.strptime(form.get('scheduled_at', ''), '%Y-%m-%dT%H:%M')
    except ValueError:
        raise ValueError('Choose a valid interview date and time.')
    return dict(interviewer=form.get('interviewer', ''), scheduled_at=when,
                venue=form.get('venue', ''), notes=' '.join(form.get('notes', '').split())[:255] or None)


def back_to_review(application):
    return redirect(url_for('registrar_applications.review', application_id=application.id))


@registrar_applications_bp.route('/<int:application_id>/approve', methods=['POST'])
@roles_required('registrar')
def approve(application_id):
    application = get_application(application_id)
    try:
        # Kung may inilagay na petsa, sabay na ang interview at isang email lang ang ipapadala
        interview = interview_from_form(request.form) if request.form.get('scheduled_at') else None
        application.approve(g.user, interview)
        AuditLog.record('Application approved', f'Application #{application.id}')
        flash('Application approved. The applicant was notified.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return back_to_review(application)


@registrar_applications_bp.route('/<int:application_id>/schedule', methods=['POST'])
@roles_required('registrar')
def schedule(application_id):
    application = get_application(application_id)
    try:
        application.schedule_interview(g.user, **interview_from_form(request.form))
        AuditLog.record('Interview scheduled', f'Application #{application.id}')
        flash('Interview scheduled. The applicant was notified.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return back_to_review(application)


@registrar_applications_bp.route('/<int:application_id>/passed', methods=['POST'])
@roles_required('registrar')
def interview_passed(application_id):
    application = get_application(application_id)
    try:
        application.pass_interview(g.user)
        AuditLog.record('Interview passed', f'Application #{application.id}')
        flash('Marked as passed. The applicant is now For Enrollment.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return back_to_review(application)


@registrar_applications_bp.route('/<int:application_id>/reject-application', methods=['POST'])
@roles_required('registrar')
def reject_application(application_id):
    application = get_application(application_id)
    try:
        application.reject(g.user, request.form.get('reason', ''))
        AuditLog.record('Application rejected', f'Application #{application.id}')
        flash('Application rejected. The applicant was notified.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return back_to_review(application)