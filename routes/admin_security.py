from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models.audit_log import AuditLog
from models.security import Security
from models.setting import Setting
from models.user import User
from utils import roles_required, Pager

admin_security_bp = Blueprint('admin_security', __name__, url_prefix='/admin/security')


@admin_security_bp.route('/')
@roles_required('admin')
def index():
    Security.purge_old()
    q = request.args.get('q', '').strip()[:80]
    kind = request.args.get('kind', '')
    pager = Pager(Security.count(q, kind), request.args.get('page', 1, type=int), per_page=15)
    rows = Security.rows(q, kind, pager.per_page, (pager.page - 1) * pager.per_page)
    return render_template('admin/security.html', rows=rows, pager=pager, q=q, kind=kind, types=Security.TYPES,
                           portals=Security.PORTAL_LABELS, summary=Security.summary(),
                           locked=Security.locked_accounts(), blocked=Security.blocked_ips(),
                           top_ips=Security.top_ips(), limit=Security.IP_LIMIT, minutes=Security.WINDOW_MINUTES,
                           max_failed=Setting.number('max_failed_logins', 5, 3, 10),
                           lock_minutes=Setting.number('lock_minutes', 15, 5, 120),
                           days=Security.RETENTION_DAYS)


@admin_security_bp.route('/unlock/<int:user_id>', methods=['POST'])
@roles_required('admin')
def unlock(user_id):
    user = User.find(user_id)
    if user is None:
        abort(404)
    user.unlock()
    AuditLog.record('Account unlocked', user.email)
    flash(f'{user.full_name} can log in again.', 'success')
    return redirect(url_for('admin_security.index'))


@admin_security_bp.route('/unblock', methods=['POST'])
@roles_required('admin')
def unblock():
    ip = request.form.get('ip', '').strip()[:45]
    if not ip:
        abort(400)
    Security.unblock_ip(ip)
    AuditLog.record('IP unblocked', ip)
    flash(f'{ip} was unblocked.', 'success')
    return redirect(url_for('admin_security.index'))