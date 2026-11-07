from flask import (Blueprint, render_template, request, flash, redirect, url_for, session, g,
                   send_file, abort)
from utils import login_required
from models.audit_log import AuditLog
from models.privacy import Privacy
from models.profile import Profile
from routes.auth import PASSWORD_RE, NAME_RE, clean_name

account_bp = Blueprint('account', __name__, url_prefix='/account')


def _page(values=None, errors=None, anchor=''):
    """Ang Settings page. Kapag may error, ipinapakita ulit ang tinype ng user."""
    for message in errors or []:
        flash(message, 'danger')
    return render_template('account/settings.html', v=values or {}, history=Privacy.history(g.user.id),
                           privacy_version=Privacy.VERSION, can_edit_name=g.user.role != 'student',
                           has_photo=Profile.photo_path(g.user) is not None, anchor=anchor)


@account_bp.route('/settings')
@login_required
def settings():
    return _page()


# ---------- larawan ----------
@account_bp.route('/photo')
@login_required
def photo():
    path = Profile.photo_path(g.user)
    if path is None:
        abort(404)
    response = send_file(path, mimetype='image/jpeg')
    response.headers['Cache-Control'] = 'private, max-age=86400'
    return response


@account_bp.route('/settings/photo', methods=['POST'])
@login_required
def photo_upload():
    upload = request.files.get('photo')
    error = Profile.save_photo(g.user, upload) if upload and upload.filename else 'Choose a photo first.'
    if error:
        flash(error, 'danger')
    else:
        AuditLog.record('Profile photo changed')
        flash('Your photo was updated.', 'success')
    return redirect(url_for('account.settings'))


@account_bp.route('/settings/photo/remove', methods=['POST'])
@login_required
def photo_remove():
    Profile.remove_photo(g.user)
    AuditLog.record('Profile photo removed')
    flash('Your photo was removed.', 'info')
    return redirect(url_for('account.settings'))


# ---------- pangalan ----------
@account_bp.route('/settings/profile', methods=['POST'])
@login_required
def profile():
    if g.user.role == 'student':
        flash('Your name is part of your school records. Please ask the Registrar to change it.', 'info')
        return redirect(url_for('account.settings'))
    first = clean_name(request.form.get('first_name', ''))
    middle = clean_name(request.form.get('middle_name', ''))
    last = clean_name(request.form.get('last_name', ''))
    errors = []
    if not (2 <= len(first) <= 50 and NAME_RE.match(first)):
        errors.append('First name must be 2 to 50 letters.')
    if middle and not (len(middle) <= 50 and NAME_RE.match(middle)):
        errors.append('Middle name may only contain letters, up to 50 characters.')
    if not (2 <= len(last) <= 50 and NAME_RE.match(last)):
        errors.append('Last name must be 2 to 50 letters.')
    if errors:
        return _page(request.form, errors, 'profile')
    Profile.update_name(g.user, first, middle, last)
    AuditLog.record('Profile updated', 'Name')
    flash('Your name was updated.', 'success')
    return redirect(url_for('account.settings'))


# ---------- password ----------
@account_bp.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'GET':
        return redirect(url_for('account.settings') + '#password')
    current = request.form.get('current_password', '')
    new = request.form.get('new_password', '')
    confirm = request.form.get('confirm', '')

    errors = []
    if not g.user.check_password(current):
        errors.append('Your current password is incorrect.')
    if not PASSWORD_RE.match(new):
        errors.append('New password needs at least 8 characters with a letter and a number.')
    if new != confirm:
        errors.append('New passwords do not match.')
    if current and new == current:
        errors.append('The new password must be different from the current one.')
    if errors:
        return _page(None, errors, 'password')

    g.user.set_password(new)
    g.user.session_version += 1                       # ibang mga device ay ma-logout
    g.user.save()
    session['session_version'] = g.user.session_version   # ang kasalukuyang device ay mananatili
    AuditLog.record('Password changed')
    flash('Your password has been changed.', 'success')
    return redirect(url_for('account.settings'))