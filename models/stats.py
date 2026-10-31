from db import query
from models.term import Term


class Stats:
    """Mga bilang para sa mga dashboard."""

    @staticmethod
    def active_students():
        return query("SELECT COUNT(*) AS n FROM users WHERE role = 'student' AND is_active = 1", one=True)['n']

    @classmethod
    def registrar(cls, term_id=None):
        """Lahat ng kailangan ng dashboard ng Registrar. Ang bukas na term ang default."""
        terms = Term.active()
        term = next((t for t in terms if t.id == term_id), terms[0] if terms else None)
        data = dict(terms=terms, term=term, students=cls.active_students(),
                    counts={}, drafts=0, total=0, programs=[])
        if term:
            rows = query("SELECT status, COUNT(*) AS n FROM applications WHERE term_id = %s GROUP BY status",
                         (term.id,))
            counts = {r['status']: r['n'] for r in rows}
            data['drafts'] = counts.pop('Draft', 0)
            data['counts'] = counts
            data['total'] = sum(counts.values())
            data['programs'] = query(
                "SELECT p.code, p.name, COUNT(*) AS n FROM applications a JOIN programs p ON p.id = a.program_id "
                "WHERE a.term_id = %s AND a.status <> 'Draft' GROUP BY p.id ORDER BY n DESC, p.code", (term.id,))
        return data