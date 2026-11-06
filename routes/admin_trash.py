from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models.audit_log import AuditLog
from models.trash import Trash
from utils import roles_required, Pager

admin_trash_bp = Blueprint('admin_trash', __name__, url_prefix='/admin/trash')


def _item(kind, item_id):
    row = Trash.find(kind, item_id)
    if row is None:
        abort(404)
    return row


@admin_trash_bp.route('/')
@roles_required('admin')
def index():
    purged = Trash.purge_expired()                         # awtomatikong linis kapag binuksan
    if purged:
        AuditLog.record('Trash purged', f'{purged} item(s) older than {Trash.DAYS} days')
        flash(f'{purged} item(s) older than {Trash.DAYS} days were removed for good.', 'info')
    q = request.args.get('q', '').strip()[:80]
    kind = request.args.get('kind', '')
    if kind not in Trash.SOURCES:
        kind = ''
    rows = Trash.items(q, kind)
    pager = Pager(len(rows), request.args.get('page', 1, type=int))
    page_rows = rows[(pager.page - 1) * pager.per_page: pager.page * pager.per_page]
    return render_template('admin/trash.html', rows=page_rows, pager=pager, q=q, kind=kind,
                           sources=Trash.SOURCES, counts=Trash.counts(), days=Trash.DAYS)


@admin_trash_bp.route('/<kind>/<int:item_id>/restore', methods=['POST'])
@roles_required('admin')
def restore(kind, item_id):
    row = _item(kind, item_id)
    Trash.restore(kind, item_id)
    AuditLog.record('Trash restored', f"{Trash.SOURCES[kind]['label']}: {row['title']}"[:200])
    flash(f"{Trash.SOURCES[kind]['label']} restored.", 'success')
    return redirect(url_for('admin_trash.index'))


@admin_trash_bp.route('/<kind>/<int:item_id>/delete', methods=['POST'])
@roles_required('admin')
def delete(kind, item_id):
    row = _item(kind, item_id)
    Trash.forever(kind, row)
    AuditLog.record('Trash deleted forever', f"{Trash.SOURCES[kind]['label']}: {row['title']}"[:200])
    flash('Deleted for good.', 'success')
    return redirect(url_for('admin_trash.index'))


@admin_trash_bp.route('/empty', methods=['POST'])
@roles_required('admin')
def empty():
    total = Trash.empty()
    AuditLog.record('Trash emptied', f'{total} item(s)')
    flash(f'Trash emptied. {total} item(s) were deleted for good.', 'success')
    return redirect(url_for('admin_trash.index'))