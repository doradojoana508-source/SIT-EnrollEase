from flask import Blueprint, render_template
from models.program import Program

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    return render_template('public/index.html', programs=Program.active())