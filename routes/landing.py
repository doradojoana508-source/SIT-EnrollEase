from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, g
from models.audit_log import AuditLog
from models.landing import Landing
from models.setting import Setting
from utils import roles_required

KEYS = {'admin': 'admin', 'registrar': 'registrar'}                       # key -> role
TITLES = {'banner': 'Banner', 'about': 'About, Vision and Mission', 'process': 'Enrollment Process',
          'requirements': 'Requirements'}


def create_landing(key, role):
    """Pag-edit ng landing page (Admin at Registrar)."""
    bp = Blueprint(f'{key}_landing', __name__, url_prefix=f'/{key}/landing')

    def _page(values=None, errors=None, open_section=''):
        base = Landing.raw()
        base.update({k: v for k, v in Setting.as_dict().items() if k.startswith(('school_', 'helpdesk'))})
        base.setdefault('helpdesk_email', 'sit.ntbc@gmail.com')
        if values:
            base.update(values)
        return render_template('landing/index.html', v=base, errors=errors or [], open_section=open_section,
                               bp=bp.name, titles=TITLES, contact_fields=Landing.CONTACT)

    @bp.route('/')
    @roles_required(role)
    def index():
        return _page()

    @bp.route('/save/<section>', methods=['POST'])
    @roles_required(role)
    def save(section):
        if section not in Landing.SECTIONS:
            abort(404)
        data, errors = Landing.clean(section, request.form)
        if errors:
            return _page(request.form, errors, section)
        Landing.save_values(data, g.user.id)
        AuditLog.record('Landing page updated', TITLES[section])
        flash(f'{TITLES[section]} saved. It is now live on the landing page.', 'success')
        return redirect(url_for(f'{bp.name}.index') + f'#{section}')

    @bp.route('/restore/<section>', methods=['POST'])
    @roles_required(role)
    def restore(section):
        if section not in Landing.SECTIONS:
            abort(404)
        Landing.restore_defaults(section)
        AuditLog.record('Landing page restored to default', TITLES[section])
        flash(f'{TITLES[section]} was restored to the original text.', 'success')
        return redirect(url_for(f'{bp.name}.index') + f'#{section}')

    @bp.route('/banner', methods=['POST'])
    @roles_required(role)
    def banner():
        error = Landing.save_banner(request.files.get('banner'), g.user.id)
        if error:
            flash(error, 'danger')
        else:
            AuditLog.record('Landing page updated', 'Banner image')
            flash('Banner image saved.', 'success')
        return redirect(url_for(f'{bp.name}.index') + '#banner')

    @bp.route('/banner/reset', methods=['POST'])
    @roles_required(role)
    def banner_reset():
        Landing.reset_banner(g.user.id)
        AuditLog.record('Landing page updated', 'Banner image removed')
        flash('The default banner is back.', 'success')
        return redirect(url_for(f'{bp.name}.index') + '#banner')

    @bp.route('/contact', methods=['POST'])
    @roles_required(role)
    def contact():
        data, errors = Landing.clean_contact(request.form)
        if errors:
            return _page(request.form, errors, 'contact')
        Landing.save_contact(data)
        AuditLog.record('Landing page updated', 'Contact information')
        flash('Contact information saved.', 'success')
        return redirect(url_for(f'{bp.name}.index') + '#contact')

    @bp.route('/programs')
    @roles_required(role)
    def programs():
        return render_template('landing/programs.html', programs=Landing.programs(), bp=bp.name)

    @bp.route('/programs/<int:program_id>', methods=['GET', 'POST'])
    @roles_required(role)
    def program(program_id):
        row = Landing.program(program_id)
        if row is None:
            abort(404)
        if request.method == 'GET':
            return render_template('landing/program_form.html', p=row, values=row, errors=[], bp=bp.name)
        data, errors = Landing.clean_program(request.form)
        if errors:
            return render_template('landing/program_form.html', p=row, values=request.form, errors=errors, bp=bp.name)
        Landing.save_program(program_id, data)
        AuditLog.record('Program text updated', f"{row['code']}: {data['name']}")
        flash(f"{row['code']} saved.", 'success')
        return redirect(url_for(f'{bp.name}.programs'))

    return bp


landing_blueprints = [create_landing(k, r) for k, r in KEYS.items()]