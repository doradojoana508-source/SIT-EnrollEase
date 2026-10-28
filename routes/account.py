from flask import Blueprint, render_template, request, flash, redirect, url_for, session, g
from utils import login_required
from routes.auth import PASSWORD_RE

account_bp = Blueprint('account', __name__, url_prefix='/account')


@account_bp.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
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
            for message in errors:
                flash(message, 'danger')
            return render_template('account/change_password.html')

        g.user.set_password(new)
        g.user.session_version += 1                       # ibang mga device ay ma-logout
        g.user.save()
        session['session_version'] = g.user.session_version   # ang kasalukuyang device ay mananatili
        flash('Your password has been changed.', 'success')
        return redirect(url_for('account.change_password'))

    return render_template('account/change_password.html')