from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from models.announcement import Announcement
from models.audit_log import AuditLog
from utils import roles_required, Pager

POSTERS = {'admin': 'admin', 'registrar': 'registrar', 'finance': 'finance'}       # key -> role
READERS = {'faculty': 'faculty', 'portal': 'student', 'applicant': 'applicant'}


def _can_edit(row):
    return g.user.role == 'admin' or row['created_by'] == g.user.id


def create_manage(key, role):
    """Pamahalaan ang mga anunsyo (Admin, Registrar, Finance)."""
    bp = Blueprint(f'{key}_announcements', __name__, url_prefix=f'/{key}/announcements')

    def _form(mode, values, errors, existing=None):
        return render_template('announcements/form.html', mode=mode, values=values, errors=errors, existing=existing,
                               audiences=Announcement.AUDIENCES, bp=bp.name)

    @bp.route('/')
    @roles_required(role)
    def index():
        q = request.args.get('q', '').strip()[:80]
        state = request.args.get('state', '')
        pager = Pager(Announcement.count(q, state), request.args.get('page', 1, type=int))
        rows = Announcement.rows(q, state, pager.per_page, (pager.page - 1) * pager.per_page)
        for r in rows:
            r['can_edit'] = _can_edit(r)
        return render_template('announcements/manage.html', rows=rows, pager=pager, q=q, state=state, bp=bp.name,
                               audiences=dict(Announcement.AUDIENCES))

    @bp.route('/new', methods=['GET', 'POST'])
    @roles_required(role)
    def new():
        if request.method == 'GET':
            return _form('create', {'audience': 'student', 'notify': '1'}, [])
        data, errors = Announcement.clean(request.form)
        if errors:
            return _form('create', request.form, errors)
        Announcement.create(data, g.user)
        AuditLog.record('Announcement posted', f"{data['title']} ({data['audience']})")
        message = 'Announcement saved.'
        live = data['publish_at'] is None or data['publish_at'] <= datetime.now()
        if request.form.get('notify') == '1' and live:
            total, emailed = Announcement.notify(data, request.form.get('email') == '1')
            message = f'Announcement posted. {total} account(s) were notified on their dashboard.'
            if request.form.get('email') == '1':
                message += (f' {emailed} email(s) sent.' if emailed is not None
                            else ' Emails were skipped because there are more than 100 recipients.')
        elif request.form.get('notify') == '1':
            message = 'Announcement scheduled. Notifications are only sent when it is published immediately.'
        flash(message, 'success')
        return redirect(url_for(f'{bp.name}.index'))

    @bp.route('/<int:announcement_id>/edit', methods=['GET', 'POST'])
    @roles_required(role)
    def edit(announcement_id):
        existing = Announcement.find(announcement_id)
        if existing is None:
            abort(404)
        if not _can_edit(existing):
            abort(403)
        if request.method == 'GET':
            return _form('edit', Announcement.to_form(existing), [], existing)
        data, errors = Announcement.clean(request.form)
        if errors:
            return _form('edit', request.form, errors, existing)
        Announcement.update(announcement_id, data)
        AuditLog.record('Announcement updated', data['title'])
        flash('Announcement updated.', 'success')
        return redirect(url_for(f'{bp.name}.index'))

    @bp.route('/<int:announcement_id>/delete', methods=['POST'])
    @roles_required(role)
    def delete(announcement_id):
        existing = Announcement.find(announcement_id)
        if existing is None:
            abort(404)
        if not _can_edit(existing):
            abort(403)
        Announcement.delete(announcement_id)
        AuditLog.record('Announcement deleted', existing['title'])
        flash('Announcement deleted.', 'success')
        return redirect(url_for(f'{bp.name}.index'))

    return bp


def create_view(key, role):
    """Basahin ang mga anunsyo (Faculty, Student, Applicant)."""
    bp = Blueprint(f'{key}_news', __name__, url_prefix=f'/{key}/news')

    @bp.route('/')
    @roles_required(role)
    def index():
        pager = Pager(Announcement.count_for(role), request.args.get('page', 1, type=int))
        rows = Announcement.for_role(role, pager.per_page, (pager.page - 1) * pager.per_page)
        return render_template('announcements/view.html', rows=rows, pager=pager)

    return bp


manage_blueprints = [create_manage(k, r) for k, r in POSTERS.items()]
view_blueprints = [create_view(k, r) for k, r in READERS.items()]