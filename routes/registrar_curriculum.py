from flask import Blueprint, render_template, abort
from models.curriculum import Curriculum
from utils import roles_required

registrar_curriculum_bp = Blueprint('registrar_curriculum', __name__, url_prefix='/registrar/curriculum')


@registrar_curriculum_bp.route('/')
@roles_required('registrar')
def index():
    return render_template('registrar/curriculum.html', programs=Curriculum.programs())


@registrar_curriculum_bp.route('/<int:program_id>')
@roles_required('registrar')
def detail(program_id):
    program = Curriculum.program(program_id)
    if program is None:
        abort(404)
    groups = Curriculum.groups(program_id)
    core = sum(g['units'] for g in groups if g['key'] == 'Core')
    extra = Curriculum.EXTRA_UNITS.get(program['code'], 0)
    return render_template('registrar/curriculum_program.html', program=program, groups=groups,
                           core=core, extra=extra)