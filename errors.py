from flask import render_template
from werkzeug.exceptions import HTTPException

# code: (pamagat, paliwanag, icon). Walang technical details na ipinapakita sa user.
MESSAGES = {
    400: ('That request could not be completed',
          'The page may have expired or the form was incomplete. Please go back, reload the page and try again.',
          'bi-exclamation-circle'),
    403: ('You do not have access to this page',
          'This page is for a different kind of account. If you think this is a mistake, please contact the school office.',
          'bi-shield-lock'),
    404: ('Page not found',
          'The page you are looking for does not exist or may have been moved.',
          'bi-compass'),
    405: ('That action is not allowed here',
          'Please use the buttons on the page instead of typing the address.',
          'bi-slash-circle'),
    413: ('The file is too large',
          'The system accepts up to 32 MB for each upload. Please choose a smaller file and try again.',
          'bi-file-earmark-x'),
    500: ('Something went wrong on our side',
          'The problem was recorded. Please try again in a moment. If it keeps happening, please tell the school office.',
          'bi-tools'),
}


def register_errors(app):
    """Friendly na error pages para sa 400, 403, 404, 405, 413 at 500."""

    def handle(error):
        code = error.code if isinstance(error, HTTPException) and error.code in MESSAGES else 500
        title, text, icon = MESSAGES[code]
        try:
            return render_template('errors/error.html', code=code, title=title, text=text, icon=icon), code
        except Exception:                      # kahit masira ang template, hindi dapat lumabas ang stack trace
            return f'{code} {title}', code

    for code in MESSAGES:
        app.register_error_handler(code, handle)