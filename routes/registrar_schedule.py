from flask import Blueprint, request, redirect, url_for, flash
from models.audit_log import AuditLog
from models.class_offering import ClassOffering
from models.scheduler import Scheduler
from utils import roles_required

registrar_schedule_bp = Blueprint('registrar_schedule', __name__, url_prefix='/registrar/schedule')


@registrar_schedule_bp.route('/auto-assign', methods=['POST'])
@roles_required('registrar')
def auto_assign():
    terms = ClassOffering.terms()
    term = ClassOffering.pick_term(terms, request.form.get('term', type=int))
    if term is None:
        return redirect(url_for('registrar_classes.index'))
    done = Scheduler.assign_missing(term['id'])
    AuditLog.record('Professors auto-assigned', f"{term['label']}: {done} class(es)")
    if done:
        flash(f'{done} class(es) now have a professor. Every COR with those classes updated.', 'success')
    else:
        flash('No professor matched the classes that still have none. Check the specialties under Faculty.', 'info')
    return redirect(url_for('registrar_classes.index', term=term['id']))