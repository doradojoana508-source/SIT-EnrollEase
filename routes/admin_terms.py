from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models.term import Term
from models.audit_log import AuditLog
from utils import roles_required

admin_terms_bp = Blueprint('admin_terms', __name__, url_prefix='/admin/terms')


def get_term(term_id):
    term = Term.find(term_id)
    if term is None:
        abort(404)
    return term


@admin_terms_bp.route('/')
@roles_required('admin')
def index():
    return render_template('admin/terms.html', terms=Term.all())


@admin_terms_bp.route('/new', methods=['GET', 'POST'])
@roles_required('admin')
def new():
    if request.method == 'POST':
        try:
            Term.create(request.form.get('term_no'), request.form.get('academic_year'),
                        request.form.get('admission_open'), request.form.get('admission_close'))
            AuditLog.record('Term created', f'{request.form.get("academic_year")} trimester {request.form.get("term_no")}')
            flash('Term added.', 'success')
            return redirect(url_for('admin_terms.index'))
        except ValueError as exc:
            flash(str(exc), 'danger')
    return render_template('admin/term_form.html', term=None, form=request.form)


@admin_terms_bp.route('/<int:term_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def edit(term_id):
    term = get_term(term_id)
    if request.method == 'POST':
        try:
            Term.update_dates(term.id, request.form.get('admission_open'), request.form.get('admission_close'))
            AuditLog.record('Term dates updated', term.short)
            flash('Dates saved.', 'success')
            return redirect(url_for('admin_terms.index'))
        except ValueError as exc:
            flash(str(exc), 'danger')
        form = request.form
    else:
        form = {'admission_open': term.admission_open.isoformat() if term.admission_open else '',
                'admission_close': term.admission_close.isoformat() if term.admission_close else ''}
    return render_template('admin/term_form.html', term=term, form=form)


@admin_terms_bp.route('/<int:term_id>/open', methods=['POST'])
@roles_required('admin')
def open_window(term_id):
    term = get_term(term_id)
    try:
        Term.open_window(term.id)
        AuditLog.record('Admission opened', term.short)
        flash(f'Admission for {term.short} is now open.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('admin_terms.index'))


@admin_terms_bp.route('/<int:term_id>/close', methods=['POST'])
@roles_required('admin')
def close_window(term_id):
    term = get_term(term_id)
    try:
        Term.close_window(term.id)
        AuditLog.record('Admission closed', term.short)
        flash(f'Admission for {term.short} is now closed.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('admin_terms.index'))