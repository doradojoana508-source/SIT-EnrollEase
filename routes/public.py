from flask import Blueprint, render_template, request
from models.announcement import Announcement
from models.landing import Landing
from models.program import Program
from models.document_type import DocumentType
from models.setting import Setting

public_bp = Blueprint('public', __name__)


def home_context():
    """Mga data ng landing page. Ginagamit din ng auth kapag may error sa form."""
    return dict(programs=Program.active(),
                documents=DocumentType.active(),
                school=Setting.as_dict(),
                announcements=Announcement.public(4),
                lc=Landing.content())


@public_bp.route('/')
def index():
    return render_template('public/index.html',
                           auth_open=request.args.get('auth'), form={}, **home_context())