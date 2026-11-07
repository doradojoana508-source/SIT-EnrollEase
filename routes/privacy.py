from flask import Blueprint, render_template, request, redirect, flash, g
from models.privacy import Privacy
from models.setting import Setting
from utils import login_required, home_url_for

privacy_bp = Blueprint('privacy', __name__, url_prefix='/privacy')


def _page(template, **context):
    return render_template(template, school=Setting.as_dict(), version=Privacy.VERSION, **context)


@privacy_bp.route('/')
def notice():
    """Ang Data Privacy Notice. Bukas sa lahat, kahit hindi naka-login."""
    return _page('privacy/notice.html')


@privacy_bp.route('/consent', methods=['GET', 'POST'])
@login_required
def consent():
    """Dito dumadaan ang lahat ng naka-login na hindi pa tumatanggap ng kasalukuyang bersyon."""
    if Privacy.has_accepted(g.user.id):
        return redirect(home_url_for(g.user.role))
    if request.method == 'POST':
        if not request.form.get('agree'):
            flash('Please tick the box to continue, or log out.', 'danger')
            return _page('privacy/consent.html')
        Privacy.accept(g.user)
        flash('Thank you. Your consent was recorded.', 'success')
        return redirect(home_url_for(g.user.role))
    return _page('privacy/consent.html')