from flask import Blueprint, render_template, request, abort, g, url_for
from models.grade import Grade
from models.transcript import Transcript
from utils import roles_required

portal_grades_bp = Blueprint('portal_grades', __name__, url_prefix='/portal/grades')


@portal_grades_bp.route('/')
@roles_required('student')
def index():
    return render_template('portal/grades.html', groups=Grade.grouped(Grade.for_student(g.user.id)))


@portal_grades_bp.route('/print')
@roles_required('student')
def print_report():
    report = Transcript.grade_report(g.user.id, request.args.get('ay', ''), request.args.get('tn', 0, type=int))
    if report is None:
        abort(404)
    return render_template('print/grade_report.html', v=report, back=url_for('portal_grades.index'))