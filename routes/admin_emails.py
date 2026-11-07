from flask import Blueprint, render_template, request
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