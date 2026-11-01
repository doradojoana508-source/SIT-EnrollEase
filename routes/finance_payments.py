from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from models.audit_log import AuditLog
from models.payment import Payment
from models.quotation import Quotation
from models.user import User
from utils import roles_required

finance_payments_bp = Blueprint('finance_payments', __name__, url_prefix='/finance/payments')


def _load(application_id):
    application = Quotation.application_for_finance(application_id)
    if application is None:
        abort(404)
    return application, Quotation.find(application.id)


@finance_payments_bp.route('/<int:application_id>', methods=['GET', 'POST'])
@roles_required('finance')
def index(application_id):
    application, quotation = _load(application_id)
    if quotation is None:
        flash('Prepare the quotation first.', 'warning')
        return redirect(url_for('finance_quotations.form', application_id=application.id))

    errors = []
    if request.method == 'POST':
        data, errors = Payment.clean(request.form, quotation)
        if not errors:
            fully_paid = Payment.record(application, quotation, data, g.user)
            AuditLog.record('Payment recorded', f'Application #{application.id}, receipt {data["receipt_no"]}')
            flash('Payment recorded. The student is now fully paid.' if fully_paid
                  else 'Payment recorded. The student was notified.', 'success')
            return redirect(url_for('finance_payments.index', application_id=application.id))
        values = request.form
    else:
        summary = Payment.summary(quotation)
        values = {'amount': '{:.2f}'.format(summary['balance']), 'paid_on': date.today().isoformat()}

    return render_template('finance/payments.html', application=application, quotation=quotation,
                           applicant=User.find(application.user_id), summary=Payment.summary(quotation),
                           history=Payment.history(quotation['id']), errors=errors, values=values,
                           today=date.today().isoformat())


@finance_payments_bp.route('/<int:application_id>/void/<int:payment_id>', methods=['POST'])
@roles_required('finance')
def void(application_id, payment_id):
    application, quotation = _load(application_id)
    if quotation is None:
        abort(404)
    try:
        row = Payment.void(application, quotation, payment_id, g.user)
        AuditLog.record('Payment voided', f'Application #{application.id}, receipt {row["receipt_no"]}')
        flash('Payment voided.', 'success')
    except ValueError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('finance_payments.index', application_id=application.id))