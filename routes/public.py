from flask import Blueprint, render_template
from models.program import Program
from models.document_type import DocumentType
from models.setting import Setting

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    return render_template('public/index.html',
                           programs=Program.active(),
                           documents=DocumentType.active(),
                           school=Setting.as_dict())