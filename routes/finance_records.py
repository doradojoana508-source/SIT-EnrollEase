from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models.audit_log import AuditLog
from models.finance_record import FinanceRecord
from models.payment import Payment
from utils import roles_required, Pager

finance_records_bp = Blueprint('finance_records', __name__, url_prefix='/finance/records')


def _record(application_id):
    row = FinanceRecord.find(application_id)
    if row is None:
        abort(404)
    return row


@finance_records_bp.route('/')
@roles_required('finance')
def index():
    q = request.args.get('q', '').strip()[:80]
    state = request.args.get('state', '')
    if state not in ('balance', 'paid'):
        state = ''
    term_id = request.args.get('term', type=int)
    archived = request.args.get('view') == 'archived'
    pager = Pager(FinanceRecord.count(q, state, term_id, archived), request.args.get('page', 1, type=int))
    rows = FinanceRecord.rows(q, state, term_id, archived, pager.per_page, (pager.page - 1) * pager.per_page)
    return render_template('finance/records.html', rows=rows, pager=pager, q=q, state=state, term_id=term_id,
                           archived=archived, terms=FinanceRecord.terms(), counts=FinanceRecord.counts())


@finance_records_bp.route('/<int:application_id>')
@roles_required('finance')
def view(application_id):
    r = _record(application_id)
    from models.quotation import Quotation
    return render_template('finance/record.html', r=r, summary=Payment.summary(r), history=Payment.history(r['id']),
                           fees=[(label, r[col]) for col, label in Quotation.FEES if r[col]],
                           can_delete=r['payment_count'] == 0 and r['app_status'] != 'Enrolled')


@finance_records_bp.route('/<int:application_id>/archive', methods=['POST'])
@roles_required('finance')
def archive(application_id):
    r = _record(application_id)
    if r['paid_at'] is None:
        flash('Only fully paid records can be archived. This student still has a balance.', 'danger')
    else:
        FinanceRecord.archive(application_id)
        AuditLog.record('Finance record archived', f"{r['student_id']}")
        flash('Record archived. You can find it under Archived.', 'success')
    return redirect(url_for('finance_records.index'))


@finance_records_bp.route('/<int:application_id>/restore', methods=['POST'])
@roles_required('finance')
def restore(application_id):
    r = _record(application_id)
    FinanceRecord.restore(application_id)
    AuditLog.record('Finance record restored', f"{r['student_id']}")
    flash('Record restored.', 'success')
    return redirect(url_for('finance_records.view', application_id=application_id))


@finance_records_bp.route('/<int:application_id>/delete', methods=['POST'])
@roles_required('finance')
def delete(application_id):
    r = _record(application_id)
    if r['payment_count'] or r['app_status'] == 'Enrolled':
        flash('This record has payments or the student is already enrolled, so it cannot be deleted. Archive it instead.', 'danger')
        return redirect(url_for('finance_records.view', application_id=application_id))
    FinanceRecord.delete(application_id)
    AuditLog.record('Quotation deleted', f"{r['student_id']}")
    flash('Quotation deleted. The applicant is back in the Quotation Queue.', 'success')
    return redirect(url_for('finance_records.index'))


@finance_records_bp.route('/<int:application_id>/receipt/<int:payment_id>')
@roles_required('finance')
def receipt(application_id, payment_id):
    row = FinanceRecord.receipt(application_id, payment_id)
    if row is None:
        abort(404)
    return render_template('print/receipt.html', r=row, back=url_for('finance_records.view', application_id=application_id))