from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from models.audit_log import AuditLog
from models.class_offering import ClassOffering
from models.cor import Cor
from utils import roles_required, Pager

registrar_cor_bp = Blueprint('registrar_cor', __name__, url_prefix='/registrar/cor')


def _term():
    terms = ClassOffering.terms()
    return terms, ClassOffering.pick_term(terms, request.values.get('term', type=int))


def _context(user_id):
    """Ang term, student at COR. 404 kapag hindi pa Paid o wala sa term."""
    terms, term = _term()
    if term is None:
        abort(404)
    student = Cor.student(user_id, term['id'])
    if student is None:
        abort(404)
    return terms, term, student


@registrar_cor_bp.route('/')
@roles_required('registrar')
def index():
    terms, term = _term()
    q = request.args.get('q', '').strip()[:80]
    rows = Cor.paid_students(term['id'], q) if term else []
    pager = Pager(len(rows), request.args.get('page', 1, type=int), 15)
    rows = rows[pager.start - 1:pager.end] if rows else []
    return render_template('registrar/cor_list.html', terms=terms, term=term, rows=rows, q=q, pager=pager)


@registrar_cor_bp.route('/<int:user_id>', methods=['GET', 'POST'])
@roles_required('registrar')
def edit(user_id):
    terms, term, student = _context(user_id)
    cor = Cor.load(user_id, term['id'])
    if cor is None:
        flash('Generate the COR first.', 'info')
        return redirect(url_for('registrar_cor.index', term=term['id']))
    errors = []
    if request.method == 'POST':
        errors = Cor.save(cor, student, request.form, request.form.get('action', 'save'), g.user)
        if not errors:
            AuditLog.record('COR updated', f"{student['student_id']}, Trimester {term['term_no']} {term['academic_year']}")
            flash('COR saved.', 'success')
            return redirect(url_for('registrar_cor.edit', user_id=user_id, term=term['id']))
        values = request.form
    else:
        values = Cor.to_form(cor)
    mine, others = Cor.add_options(cor, student, term['id'])
    quoted = format(student['quoted_units'].normalize(), 'f')
    return render_template('registrar/cor_form.html', term=term, student=student, cor=cor, values=values,
                           errors=errors, years=Cor.YEARS, heading=Cor.heading(term),
                           trimester=Cor.trimester_label(term), mine=mine, others=others, quoted=quoted,
                           units_match=cor['total_units'] == student['quoted_units'])


@registrar_cor_bp.route('/<int:user_id>/generate', methods=['POST'])
@roles_required('registrar')
def generate(user_id):
    terms, term, student = _context(user_id)
    try:
        count = Cor.generate(student, term, g.user)
    except ValueError as error:
        flash(str(error), 'danger')
        return redirect(url_for('registrar_cor.index', term=term['id']))
    AuditLog.record('COR generated', f"{student['student_id']}, {count} subjects")
    flash(f'COR generated with {count} subject(s). Review and edit it below.', 'success')
    return redirect(url_for('registrar_cor.edit', user_id=user_id, term=term['id']))


@registrar_cor_bp.route('/<int:user_id>/regenerate', methods=['POST'])
@roles_required('registrar')
def regenerate(user_id):
    terms, term, student = _context(user_id)
    cor = Cor.load(user_id, term['id'])
    if cor is None:
        abort(404)
    count = Cor.regenerate(cor, student, term)
    AuditLog.record('COR regenerated', f"{student['student_id']}, {count} subjects")
    flash(f'Subjects were filled in again ({count}).', 'success')
    return redirect(url_for('registrar_cor.edit', user_id=user_id, term=term['id']))