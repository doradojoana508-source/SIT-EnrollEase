from db import query


class PendingStudent:
    """Mga Enrolled na wala pang Student account (applicant pa rin ang role)."""

    _SQL = ("SELECT u.id AS user_id, u.first_name, u.middle_name, u.last_name, u.email, "
            "q.student_id, a.birthdate, p.code AS program_code, t.term_no, t.academic_year "
            "FROM enrollments e JOIN users u ON u.id = e.user_id AND u.role = 'applicant' "
            "JOIN applications a ON a.user_id = u.id JOIN quotations q ON q.application_id = a.id "
            "JOIN programs p ON p.id = a.program_id JOIN academic_terms t ON t.id = e.term_id "
            "WHERE e.status = 'Enrolled'")

    @classmethod
    def all(cls):
        return query(cls._SQL + " ORDER BY e.enrolled_at, u.last_name")

    @classmethod
    def find(cls, user_id):
        return query(cls._SQL + " AND u.id = %s", (user_id,), one=True)