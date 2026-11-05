from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from models.audit_log import AuditLog
from models.class_offering import ClassOffering
from models.faculty import Faculty
from utils import roles_required

registrar_classes_bp = Blueprint('registrar_classes', __name__, url_prefix='/registrar/classes')


def _term():
    terms = ClassOffering.terms()
    return terms, ClassOffering.pick_term(terms, request.values.get('term', type=int))


def _form_page(term, mode, values, errors, existing=None):
    return render_template('registrar/class_form.html', term=term, mode=mode, values=values, errors=errors,
                           existing=existing, options=ClassOffering.subject_options(),
                           faculty=Faculty.options(), days=ClassOffering.DAYS, statuses=ClassOffering.STATUSES)


@registrar_classes_bp.route('/')
@roles_required('registrar')
def index():
    terms, term = _term()
    q = request.args.get('q', '').strip()[:80]
    rows = ClassOffering.for_term(term['id'], q) if term else []
    return render_template('registrar/classes.html', terms=terms, term=term, rows=rows, q=q)


@registrar_classes_bp.route('/new', methods=['GET', 'POST'])
@roles_required('registrar')
def create():
    terms, term = _term()
    if term is None:
        abort(404)
    errors = []
    if request.method == 'POST':
        data, errors = ClassOffering.clean(request.form, term['id'])
        if not errors:
            class_id = ClassOffering.create(term['id'], data, g.user)
            AuditLog.record('Class added', f'Class #{class_id}: {data["title"]}')
            flash('Class added.', 'success')
            return redirect(url_for('registrar_classes.index', term=term['id']))
        values = request.form
    else:
        values = {'day_code': 'TH', 'status': 'Tentative'}
    return _form_page(term, 'create', values, errors)


@registrar_classes_bp.route('/<int:class_id>/edit', methods=['GET', 'POST'])
@roles_required('registrar')
def edit(class_id):
    existing = ClassOffering.find(class_id)
    if existing is None:
        abort(404)
    term = next((t for t in ClassOffering.terms() if t['id'] == existing['term_id']), None)
    if term is None:                                   # archived na ang term
        abort(404)
    errors = []
    if request.method == 'POST':
        data, errors = ClassOffering.clean(request.form, term['id'], existing)
        if not errors:
            ClassOffering.update(existing, data)
            AuditLog.record('Class updated', f'Class #{class_id}: {existing["title"]}')
            flash('Class updated.', 'success')
            return redirect(url_for('registrar_classes.index', term=term['id']))
        values = request.form
    else:
        values = ClassOffering.to_form(existing)
    return _form_page(term, 'edit', values, errors, existing)


@registrar_classes_bp.route('/<int:class_id>/delete', methods=['POST'])
@roles_required('registrar')
def delete(class_id):
    existing = ClassOffering.find(class_id)
    if existing is None:
        abort(404)
    if existing['student_count']:
        flash(f"This class has {existing['student_count']} enrolled student(s). Remove it from their COR first.", 'danger')
        return redirect(url_for('registrar_classes.index', term=existing['term_id']))
    ClassOffering.delete(class_id)
    AuditLog.record('Class deleted', f'Class #{class_id}: {existing["title"]}')
    flash('Class deleted.', 'success')
    return redirect(url_for('registrar_classes.index', term=existing['term_id']))