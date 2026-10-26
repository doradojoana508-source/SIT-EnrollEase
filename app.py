from flask import Flask
from flask_wtf.csrf import CSRFProtect
from config import SECRET_KEY
from routes.public import public_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True        # hindi mababasa ng JavaScript ang cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'       # dagdag na proteksyon laban sa CSRF
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024 # 32 MB: kasya ang mga ebook ng LMS

csrf = CSRFProtect(app)                             # lahat ng POST form ay kailangan ng csrf_token

app.register_blueprint(public_bp)

if __name__ == '__main__':
    app.run(debug=True)