from decimal import Decimal
from db import query
from models.cor import Cor
from models.notification import Notification
from models.payment import Payment
from models.quotation import Quotation


class StudentRecord:
    """Ang nakikita ng student sa portal niya: COR at schedule, tuition at balance. Laging galing sa database (realtime)."""

    @staticmethod
    def cors(user_id):
        """Lahat ng COR ng student, pinakabago muna."""
        rows = query(
            "SELECT c.*, t.term_no, t.academic_year, p.name AS program_name, p.code AS program_code "
            "FROM cors c JOIN academic_terms t ON t.id = c.term_id JOIN programs p ON p.id = c.program_id "
            "WHERE c.user_id = %s ORDER BY t.academic_year DESC, t.term_no DESC", (user_id,))
        for r in rows:
            r['term_label'] = f"Trimester {r['term_no']}, {r['academic_year']}"
        return rows

    @staticmethod
    def _long_date(d):
        return f"{d:%B} {d.day}, {d.year}" if d else ''

    @classmethod
    def cor_view(cls, user, term_id=None):
        """Ibinabalik ang (listahan ng COR, ang napiling COR para ipakita). Ang napili ay None kung wala pa."""
        rows = cls.cors(user.id)
        if not rows:
            return rows, None
        chosen = next((r for r in rows if r['term_id'] == term_id), rows[0])
        cor = Cor.load(user.id, chosen['term_id'])
        term = {'term_no': chosen['term_no'], 'academic_year': chosen['academic_year']}
        return rows, {'cor': cor, 'term_id': chosen['term_id'], 'heading': Cor.heading(term),
                      'trimester': Cor.trimester_label(term), 'program': chosen['program_name'],
                      'name': user.formal_name, 'student_id': user.username,
                      'date_enrolled': cls._long_date(cor['date_enrolled'])}

    @classmethod
    def tuition(cls, user_id):
        """Ang quotation, mga bayad at balance. None kung wala pang quotation."""
        q = query("SELECT q.* FROM quotations q JOIN applications a ON a.id = q.application_id "
                  "WHERE a.user_id = %s", (user_id,), one=True)
        if q is None:
            return None
        return {'q': q, 'summary': Payment.summary(q),
                'fees': [(label, q[col]) for col, label in Quotation.FEES if q[col]],
                'payments': [p for p in Payment.history(q['id']) if p['voided_at'] is None]}

    @classmethod
    def dashboard(cls, user):
        rows = cls.cors(user.id)
        tuition = cls.tuition(user.id)
        return {'name': user.full_name, 'student_id': user.username,
                'latest_row': rows[0] if rows else None,
                'latest': Cor.load(user.id, rows[0]['term_id']) if rows else None,
                'tuition': tuition,
                'balance': tuition['summary']['balance'] if tuition else Decimal('0'),
                'notices': Notification.unread_for(user.id)}