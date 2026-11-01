from flask import Blueprint, render_template, request
from models.finance import Finance
from utils import roles_required, Pager

finance_queue_bp = Blueprint('finance_queue', __name__, url_prefix='/finance/queue')


@finance_queue_bp.route('/')
@roles_required('finance')
def index():
    q = request.args.get('q', '').strip()[:80]
    pager = Pager(Finance.queue_count(q), request.args.get('page', 1, type=int))
    rows = Finance.queue(q, pager.per_page, (pager.page - 1) * pager.per_page)
    return render_template('finance/queue.html', rows=rows, q=q, pager=pager)