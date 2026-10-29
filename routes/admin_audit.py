from flask import Blueprint, render_template, request
from models.audit_log import AuditLog
from utils import roles_required, Pager

admin_audit_bp = Blueprint('admin_audit', __name__, url_prefix='/admin/audit')
PER_PAGE = 15


@admin_audit_bp.route('/')
@roles_required('admin')
def index():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    rows, total = AuditLog.search(q, PER_PAGE, (max(page, 1) - 1) * PER_PAGE)
    pager = Pager(total, page, PER_PAGE)
    return render_template('admin/audit.html', rows=rows, pager=pager, q=q)