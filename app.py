import time
from datetime import timedelta
from flask import Flask, g, request, session, flash
from flask_wtf.csrf import CSRFProtect
from config import SECRET_KEY, MAIL_USERNAME, MAIL_PASSWORD
from mailer import mail
from models.user import User
from routes.public import public_bp
from routes.auth import auth_bp
from routes.account import account_bp
from routes.dashboard import dashboard_bp
from routes.applicant import applicant_bp
from routes.portals import PORTALS, create_portal
from menus import menu_for, ROLE_LABELS, ACCOUNT_MENU
from routes.admin_users import admin_users_bp
from routes.admin_audit import admin_audit_bp
from routes.registrar_applications import registrar_applications_bp
from routes.admin_terms import admin_terms_bp
from models.term import Term
from routes.registrar_admission import registrar_admission_bp
from routes.registrar_archive import registrar_archive_bp
from routes.admin_archive import admin_archive_bp
from routes.finance_queue import finance_queue_bp
from routes.finance_quotations import finance_quotations_bp
from routes.finance_payments import finance_payments_bp
from routes.registrar_curriculum import registrar_curriculum_bp
from routes.registrar_classes import registrar_classes_bp
from routes.registrar_faculty import registrar_faculty_bp
from routes.registrar_cor import registrar_cor_bp
from routes.admin_pending import admin_pending_bp
from routes.registrar_schedule import registrar_schedule_bp
from routes.portal_student import portal_student_bp
from routes.finance_records import finance_records_bp
from routes.registrar_records import registrar_records_bp
from routes.faculty_classes import faculty_classes_bp
from routes.portal_grades import portal_grades_bp
from routes.portal_enroll import portal_enroll_bp
from routes.announcements import manage_blueprints, view_blueprints
from routes.landing import landing_blueprints

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)   # maximum ng "Remember me"
IDLE_SECONDS = 30 * 60               # session timeout kapag walang ginagawa
REMEMBER_SECONDS = 7 * 24 * 3600     # timeout kapag naka-check ang Remember me
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER=('SIT-EnrollEase HelpDesk', MAIL_USERNAME),
)

csrf = CSRFProtect(app)
mail.init_app(app)


@app.before_request
def load_current_user():
    """Sa bawat request: alamin kung sino ang naka-login at kung valid pa ang session niya."""
    g.user = None
    if request.endpoint == 'static':
        return
    user_id = session.get('user_id')
    if user_id is None:
        return

    now = int(time.time())
    limit = REMEMBER_SECONDS if session.get('remember') else IDLE_SECONDS
    if now - session.get('last_seen', now) > limit:      # idle timeout
        session.clear()
        flash('Your session expired. Please log in again.', 'warning')
        return

    user = User.find(user_id)
    if user is None or not user.is_active or user.session_version != session.get('session_version'):
        session.clear()
        return
    session['last_seen'] = now
    g.user = user



@app.context_processor
def inject_user():
    user = g.get('user')
    context = {'current_user': user}
    if user:
        context.update(menu=menu_for(user.role), account_menu=ACCOUNT_MENU,
                       role_label=ROLE_LABELS.get(user.role, user.role.title()))
    return context

@app.context_processor
def inject_admission():
    """Para sa mga template: admission_window() ay ang bukas na term, o None. Isang query lang kada request."""
    def admission_window():
        if 'admission' not in g:
            g.admission = Term.open_term()
        return g.admission
    return {'admission_window': admission_window}

app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(account_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(applicant_bp)
for key, cfg in PORTALS.items():
    app.register_blueprint(create_portal(key, cfg))
app.register_blueprint(admin_users_bp)
app.register_blueprint(admin_audit_bp)
app.register_blueprint(registrar_applications_bp)
app.register_blueprint(admin_terms_bp)
app.register_blueprint(registrar_admission_bp)
app.register_blueprint(registrar_archive_bp)
app.register_blueprint(admin_archive_bp)
app.register_blueprint(finance_queue_bp)
app.register_blueprint(finance_quotations_bp)
app.register_blueprint(finance_payments_bp)
app.register_blueprint(registrar_curriculum_bp)
app.register_blueprint(registrar_classes_bp)
app.register_blueprint(registrar_faculty_bp)
app.register_blueprint(registrar_cor_bp)
app.register_blueprint(admin_pending_bp)
app.register_blueprint(registrar_schedule_bp)
app.register_blueprint(portal_student_bp)
app.register_blueprint(finance_records_bp)
app.register_blueprint(registrar_records_bp)
app.register_blueprint(faculty_classes_bp)
app.register_blueprint(portal_grades_bp)
app.register_blueprint(portal_enroll_bp)
for blueprint in (*manage_blueprints, *view_blueprints, *landing_blueprints):
    app.register_blueprint(blueprint)

if __name__ == '__main__':
    app.run(debug=True)