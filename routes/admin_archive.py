from flask import Blueprint, render_template, redirect, url_for, flash, abort
from models.term import Term
from models.audit_log import AuditLog
from utils import roles_required

admin_archive_bp = Blueprint('admin_archive', __name__, url_prefix='/admin/archive')


@admin_archive_bp.route('/')
@roles_required('admin')
def index():
    return render_template('admin/archive.html', terms=Term.archived())


@admin_archive_bp.route('/<int:term_id>/restore', methods=['POST'])
@roles_required('admin')
def restore(term_id):
    term = Term.find(term_id)
    if term is None:
        abort(404)
    try:
        Term.restore(term.id)
        AuditLog.record('Term restored', term.short)
        flash(f'{term.short} was restored. It is now Closed and back in the active lists.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('admin_archive.index'))