from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from models.application import Application
from models.audit_log import AuditLog
from models.quotation import Quotation
from models.user import User
from utils import roles_required

finance_quotations_bp = Blueprint('finance_quotations', __name__, url_prefix='/finance/quotations')


@finance_quotations_bp.route('/<int:application_id>', methods=['GET', 'POST'])
@roles_required('finance')
def form(application_id):
    application = Quotation.application_for_finance(application_id)
    if application is None:
        abort(404)
    existing = Quotation.find(application.id)
    errors = []

    if request.method == 'POST':
        data, errors = Quotation.clean(request.form, application.id)
        if not errors:
            try:
                created = Quotation.save(application, data, g.user)
                AuditLog.record('Quotation saved' if created else 'Quotation updated',
                                f'Application #{application.id}, Student ID {data["student_id"]}')
                flash('Quotation saved. The applicant was notified.' if created
                      else 'Quotation updated. The applicant was notified.', 'success')
                return redirect(url_for('finance_queue.index'))
            except ValueError as exc:
                errors.append(str(exc))
        values = request.form
    elif existing:
        values = Quotation.to_form(existing)
    else:
        values = {'account_no': Quotation.suggest_account_no()}
        owner = User.find(application.user_id)
        if owner.role == 'student':
            values['student_id'] = owner.username

    return render_template('finance/quotation_form.html', application=application,
                           applicant=User.find(application.user_id),
                           program=dict(Application.program_options()).get(application.program_id, '-'),
                           existing=existing, errors=errors, values=values, fees=Quotation.FEES)