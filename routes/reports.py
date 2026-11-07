from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, Response
from models.audit_log import AuditLog
from models.report import Report
from utils import roles_required


def create_reports(key):
    """Reports na CSV para sa isang role (registrar, finance o admin)."""
    bp = Blueprint(f'{key}_reports', __name__, url_prefix=f'/{key}/reports')

    @bp.route('/')
    @roles_required(key)
    def index():
        return render_template('reports/index.html', reports=Report.for_role(key), terms=Report.term_options(),
                               default_term=Report.default_term(), endpoint=f'{key}_reports.download')

    @bp.route('/<report_key>')
    @roles_required(key)
    def download(report_key):
        spec = Report.find(key, report_key)
        if spec is None:
            abort(404)
        values, errors = Report.clean(spec, request.args)
        if errors:
            for message in errors:
                flash(message, 'danger')
            return redirect(url_for(f'{key}_reports.index'))
        text, count = Report.csv_text(spec, values)
        AuditLog.record('Report downloaded', f'{spec.title}, {count} row(s)')
        filename = f"SIT-{spec.key}-{datetime.now():%Y%m%d-%H%M}.csv"
        return Response(text, mimetype='text/csv', headers={
            'Content-Disposition': f'attachment; filename="{filename}"', 'Cache-Control': 'no-store'})

    return bp


report_blueprints = [create_reports(role) for role in ('registrar', 'finance', 'admin')]