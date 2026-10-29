from flask import Blueprint, render_template
from utils import roles_required

applicant_bp = Blueprint('applicant', __name__, url_prefix='/applicant')


@applicant_bp.route('/dashboard')
@roles_required('applicant')
def dashboard():
    return render_template('app_home.html', heading='Applicant Dashboard')