from flask import Blueprint, render_template
from utils import login_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def home():
    return render_template('dashboard.html')