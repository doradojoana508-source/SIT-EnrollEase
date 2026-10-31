from flask import Blueprint, render_template, request, url_for, abort, send_from_directory
from models.application import Application
from models.application_document import ApplicationDocument
from models.term import Term
from models.user import User
from utils import roles_required, Pager
from routes.registrar_applications import get_doc_row, STATUS_FILTERS, PER_PAGE

registrar_archive_bp = Blueprint('registrar_archive', __name__, url_prefix='/registrar/archive')


def archived_term(term_id):
    term = Term.find(term_id)
    if term is None or term.admission_status != 'Archived':
        abort(404)
    return term


def archived_application(application_id):
    """Application na nasa naka-archive na term lang, at hindi Draft."""
    application = Application.find(application_id)
    if application is None or application.status == 'Draft' or not application.term_id:
        abort(404)
    archived_term(application.term_id)
    return application


@registrar_archive_bp.route('/')
@roles_required('registrar')
def index():
    return render_template('registrar/archive.html', terms=Term.archived())


@registrar_archive_bp.route('/term/<int:term_id>')
@roles_required('registrar')
def term_view(term_id):
    term = archived_term(term_id)
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '')
    if status not in STATUS_FILTERS:
        status = ''
    page = request.args.get('page', 1, type=int)
    rows, total = Application.search(q, status, PER_PAGE, (max(page, 1) - 1) * PER_PAGE, term.id)
    pager = Pager(total, page, PER_PAGE)
    return render_template('registrar/archive_term.html', term=term, rows=rows, pager=pager, q=q, status=status,
                           statuses=STATUS_FILTERS, programs=dict(Application.program_options()))


@registrar_archive_bp.route('/application/<int:application_id>')
@roles_required('registrar')
def view(application_id):
    application = archived_application(application_id)
    return render_template('registrar/review.html', application=application,
                           owner=User.find(application.user_id),
                           program=dict(Application.program_options()).get(application.program_id),
                           rows=application.document_rows(), interview=application.current_interview(),
                           can_review=False, read_only=True,
                           file_ep='registrar_archive.document_file',
                           back_url=url_for('registrar_archive.term_view', term_id=application.term_id))


@registrar_archive_bp.route('/application/<int:application_id>/documents/<int:type_id>/file')
@roles_required('registrar')
def document_file(application_id, type_id):
    application = archived_application(application_id)
    upload = get_doc_row(application, type_id)['upload']
    if not upload:
        abort(404)
    response = send_from_directory(ApplicationDocument.folder(application.id), upload['stored_name'],
                                   mimetype=upload['mime_type'], download_name=upload['original_name'])
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response