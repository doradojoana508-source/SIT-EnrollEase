from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from mailer import send_email
from models.audit_log import AuditLog
from models.email_log import EmailLog
from utils import roles_required, Pager

admin_emails_bp = Blueprint('admin_emails', __name__, url_prefix='/admin/emails')


@admin_emails_bp.route('/')
@roles_required('admin')
def index():
    EmailLog.purge_old()
    q = request.args.get('q', '').strip()[:80]
    status = request.args.get('status', '')
    pager = Pager(EmailLog.count(q, status), request.args.get('page', 1, type=int), per_page=15)
    rows = EmailLog.rows(q, status, pager.per_page, (pager.page - 1) * pager.per_page)
    return render_template('admin/emails.html', rows=rows, pager=pager, q=q, status=status,
                           counts=EmailLog.counts(), statuses=EmailLog.STATUSES, days=EmailLog.RETENTION_DAYS)


@admin_emails_bp.route('/test', methods=['POST'])
@roles_required('admin')
def test():
    """Nagpapadala ng test email sa sariling email ng Admin, para malaman kung gumagana ang email setup."""
    sent = send_email('SIT-EnrollEase test email', g.user.email, 'notice', user=g.user, heading='Test email',
                      message='This is a test email from SIT-EnrollEase. If you can read this, email sending works.',
                      details=[], checklist=[], link=url_for('dashboard.home', _external=True))
    AuditLog.record('Test email sent' if sent else 'Test email failed', g.user.email)
    flash(f'A test email was sent to {g.user.email}.' if sent
          else 'The test email could not be sent. See the Note column below for the reason.',
          'success' if sent else 'danger')
    return redirect(url_for('admin_emails.index'))