from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models.term import Term
from models.audit_log import AuditLog
from utils import roles_required

registrar_admission_bp = Blueprint('registrar_admission', __name__, url_prefix='/registrar/admission')
EP = 'registrar_admission'


def get_term(term_id):
    term = Term.find(term_id)
    if term is None:
        abort(404)
    return term


@registrar_admission_bp.route('/')
@roles_required('registrar')
def index():
    return render_template('admin/terms.html', terms=Term.all(), ep=EP, can_add=False,
                           heading='Admission Windows')


@registrar_admission_bp.route('/<int:term_id>/edit', methods=['GET', 'POST'])
@roles_required('registrar')
def edit(term_id):
    term = get_term(term_id)
    if request.method == 'POST':
        try:
            Term.update_dates(term.id, request.form.get('admission_open'), request.form.get('admission_close'))
            AuditLog.record('Term dates updated', term.short)
            flash('Dates saved.', 'success')
            return redirect(url_for(f'{EP}.index'))
        except ValueError as exc:
            flash(str(exc), 'danger')
        form = request.form
    else:
        form = {'admission_open': term.admission_open.isoformat() if term.admission_open else '',
                'admission_close': term.admission_close.isoformat() if term.admission_close else ''}
    return render_template('admin/term_form.html', term=term, form=form, ep=EP)


@registrar_admission_bp.route('/<int:term_id>/open', methods=['POST'])
@roles_required('registrar')
def open_window(term_id):
    term = get_term(term_id)
    try:
        Term.open_window(term.id)
        AuditLog.record('Admission opened', term.short)
        flash(f'Admission for {term.short} is now open.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for(f'{EP}.index'))


@registrar_admission_bp.route('/<int:term_id>/close', methods=['POST'])
@roles_required('registrar')
def close_window(term_id):
    term = get_term(term_id)
    try:
        Term.close_window(term.id)
        AuditLog.record('Admission closed', term.short)
        flash(f'Admission for {term.short} is now closed.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for(f'{EP}.index'))

@registrar_admission_bp.route('/<int:term_id>/archive', methods=['POST'])
@roles_required('registrar')
def archive(term_id):
    term = get_term(term_id)
    try:
        Term.archive(term.id)
        AuditLog.record('Term archived', term.short)
        flash(f'{term.short} was archived.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for(f'{EP}.index'))