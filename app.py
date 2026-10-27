from datetime import timedelta
from flask import Flask, g, request, session
from flask_wtf.csrf import CSRFProtect
from config import SECRET_KEY
from models.user import User
from routes.public import public_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)   # session timeout
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

csrf = CSRFProtect(app)


@app.before_request
def load_current_user():
    """Sa bawat request, alamin kung sino ang naka-login at kung valid pa ang session niya."""
    g.user = None
    if request.endpoint == 'static':
        return
    user_id = session.get('user_id')
    if user_id is None:
        return
    user = User.find(user_id)
    # Nawawala ang session kapag na-deactivate ang user o na-force logout (nagbago ang session_version)
    if user is None or not user.is_active or user.session_version != session.get('session_version'):
        session.clear()
        return
    g.user = user


@app.context_processor
def inject_user():
    return {'current_user': g.get('user')}      # magagamit sa lahat ng template


app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)

if __name__ == '__main__':
    app.run(debug=True)