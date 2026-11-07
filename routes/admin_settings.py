from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.audit_log import AuditLog
from models.setting import Setting
from utils import roles_required

admin_settings_bp = Blueprint('admin_settings', __name__, url_prefix='/admin/settings')


def _page(values, errors=None):
    return render_template('admin/settings.html', groups=Setting.FIELDS, values=values, errors=errors or [])


@admin_settings_bp.route('/', methods=['GET', 'POST'])
@roles_required('admin')
def index():
    if request.method == 'GET':
        return _page(Setting.numbers())
    data, errors = Setting.clean_numbers(request.form)
    if errors:
        return _page(request.form, errors)
    before = Setting.numbers()
    Setting.save_numbers(data)
    changed = [f'{k} {before[k]}->{v}' for k, v in data.items() if before[k] != v]
    AuditLog.record('Settings updated', ', '.join(changed)[:250] if changed else 'No changes')
    flash('Settings saved. They apply right away.' if changed else 'Nothing was changed.', 'success' if changed else 'info')
    return redirect(url_for('admin_settings.index'))


@admin_settings_bp.route('/restore', methods=['POST'])
@roles_required('admin')
def restore():
    Setting.restore_numbers()
    AuditLog.record('Settings restored to default')
    flash('All settings are back to their original values.', 'success')
    return redirect(url_for('admin_settings.index'))