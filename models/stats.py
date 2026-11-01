from db import query
from models.term import Term

STUDENT_TYPES = ('New', 'Transferee', 'Continuing', 'Returnee')


class Stats:
    """Mga bilang para sa mga dashboard."""

    @staticmethod
    def enrolled_by_type(term_id):
        """Ilang student ang Enrolled na sa term na ito, ayon sa uri nila."""
        rows = query("SELECT student_type, COUNT(*) AS n FROM enrollments "
                     "WHERE term_id = %s AND status = 'Enrolled' GROUP BY student_type", (term_id,))
        counts = {r['student_type']: r['n'] for r in rows}
        return {t: counts.get(t, 0) for t in STUDENT_TYPES}

    @classmethod
    def registrar(cls, term_id=None):
        """Lahat ng kailangan ng dashboard ng Registrar. Ang bukas na term ang default."""
        terms = Term.active()
        term = next((t for t in terms if t.id == term_id), terms[0] if terms else None)
        current = Term.current()
        by_type = cls.enrolled_by_type(current.id) if current else {t: 0 for t in STUDENT_TYPES}
        data = dict(terms=terms, term=term, counts={}, drafts=0, total=0, programs=[], types={},
                    current_term=current, by_type=by_type, enrolled_total=sum(by_type.values()))
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
            type_rows = query("SELECT applicant_type, COUNT(*) AS n FROM applications "
                              "WHERE term_id = %s AND status <> 'Draft' GROUP BY applicant_type", (term.id,))
            data['types'] = {r['applicant_type']: r['n'] for r in type_rows}
        return data