from flask import Blueprint, redirect, g
from utils import login_required, home_url_for

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def home():
    return redirect(home_url_for(g.user.role))