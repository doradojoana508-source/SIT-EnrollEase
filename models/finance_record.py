from db import query, execute


class FinanceRecord:
    """Student Records ng Finance: lahat ng quotation at bayad, kahit Enrolled na. May edit, archive at delete."""

    FROM = ("FROM quotations q JOIN applications a ON a.id = q.application_id JOIN users u ON u.id = a.user_id "
            "LEFT JOIN programs p ON p.id = a.program_id LEFT JOIN academic_terms t ON t.id = a.term_id")
    SCOPE = "(t.admission_status IS NULL OR t.admission_status <> 'Archived')"     # ang archived na term ay hiwalay
    PAID = ("(SELECT COALESCE(SUM(pm.amount), 0) FROM payments pm "
            "WHERE pm.quotation_id = q.id AND pm.voided_at IS NULL)")

    @staticmethod
    def terms():
        rows = query("SELECT id, term_no, academic_year FROM academic_terms WHERE admission_status <> 'Archived' "
                     "ORDER BY academic_year DESC, term_no DESC")
        for r in rows:
            r['label'] = f"Trimester {r['term_no']}, {r['academic_year']}"
        return rows

    @classmethod
    def _where(cls, q='', state='', term_id=None, archived=False):
        where = [cls.SCOPE, 'q.archived_at IS NOT NULL' if archived else 'q.archived_at IS NULL']
        params = []
        if state == 'balance':
            where.append('q.paid_at IS NULL')
        elif state == 'paid':
            where.append('q.paid_at IS NOT NULL')
        if term_id:
            where.append('a.term_id = %s')
            params.append(term_id)
        if q:
            like = f'%{q}%'
            where.append('(u.first_name LIKE %s OR u.last_name LIKE %s OR q.student_id LIKE %s OR q.account_no LIKE %s)')
            params += [like] * 4
        return ' AND '.join(where), params

    @classmethod
    def count(cls, q='', state='', term_id=None, archived=False):
        where, params = cls._where(q, state, term_id, archived)
        return query(f'SELECT COUNT(*) AS n {cls.FROM} WHERE {where}', params, one=True)['n']

    @classmethod
    def rows(cls, q='', state='', term_id=None, archived=False, limit=10, offset=0):
        where, params = cls._where(q, state, term_id, archived)
        return query(
            'SELECT a.id AS application_id, a.status AS app_status, u.first_name, u.last_name, '
            'p.code AS program_code, t.term_no, t.academic_year, q.id AS quotation_id, q.student_id, '
            f'q.account_no, q.total, q.paid_at, {cls.PAID} AS paid {cls.FROM} WHERE {where} '
            'ORDER BY q.created_at DESC, q.id DESC LIMIT %s OFFSET %s', params + [limit, offset])

    @classmethod
    def counts(cls):
        return {'active': cls.count(), 'balance': cls.count(state='balance'), 'paid': cls.count(state='paid'),
                'archived': cls.count(archived=True)}

    @classmethod
    def find(cls, application_id):
        """Ang buong record: quotation (q.*), student, program, term, at kabuuang bayad."""
        row = query(
            'SELECT q.*, a.id AS application_id, a.status AS app_status, a.user_id, u.first_name, u.middle_name, '
            'u.last_name, u.email, u.role, p.name AS program_name, p.code AS program_code, t.term_no, '
            f't.academic_year, {cls.PAID} AS paid {cls.FROM} WHERE a.id = %s', (application_id,), one=True)
        if row:
            row['payment_count'] = query("SELECT COUNT(*) AS n FROM payments WHERE quotation_id = %s",
                                         (row['id'],), one=True)['n']
            row['term_label'] = f"Trimester {row['term_no']}, {row['academic_year']}" if row['term_no'] else '-'
        return row

    # ---------- archive at delete ----------
    @staticmethod
    def archive(application_id):
        execute("UPDATE quotations SET archived_at = NOW() WHERE application_id = %s", (application_id,))

    @staticmethod
    def restore(application_id):
        execute("UPDATE quotations SET archived_at = NULL WHERE application_id = %s", (application_id,))

    @staticmethod
    def delete(application_id):
        """Buburahin ang quotation na walang bayad at hindi pa Enrolled. Mawawala rin ang 'Quoted' na enrollment."""
        execute("DELETE FROM enrollments WHERE status = 'Quoted' "
                "AND user_id = (SELECT user_id FROM applications WHERE id = %s) "
                "AND term_id = (SELECT term_id FROM applications WHERE id = %s)", (application_id, application_id))
        execute("DELETE FROM quotations WHERE application_id = %s", (application_id,))

    # ---------- resibo ----------
    @staticmethod
    def receipt(application_id, payment_id):
        row = query(
            "SELECT pm.*, q.student_id, q.account_no, q.total, u.first_name, u.middle_name, u.last_name, "
            "p.name AS program_name, t.term_no, t.academic_year, rb.first_name AS rb_first, rb.last_name AS rb_last "
            "FROM payments pm JOIN quotations q ON q.id = pm.quotation_id "
            "JOIN applications a ON a.id = q.application_id JOIN users u ON u.id = a.user_id "
            "LEFT JOIN programs p ON p.id = a.program_id LEFT JOIN academic_terms t ON t.id = a.term_id "
            "LEFT JOIN users rb ON rb.id = pm.recorded_by WHERE a.id = %s AND pm.id = %s",
            (application_id, payment_id), one=True)
        if row is None:
            return None
        upto = query("SELECT COALESCE(SUM(amount), 0) AS n FROM payments WHERE quotation_id = %s "
                     "AND voided_at IS NULL AND id <= %s", (row['quotation_id'], payment_id), one=True)['n']
        middle = f" {row['middle_name'][0].upper()}." if row['middle_name'] else ''
        row['name'] = f"{row['last_name'].upper()}, {row['first_name'].upper()}{middle}"
        row['balance_after'] = max(row['total'] - upto, 0)
        row['received_by'] = f"{row['rb_first']} {row['rb_last']}" if row['rb_first'] else ''
        row['term_label'] = f"Trimester {row['term_no']}, {row['academic_year']}" if row['term_no'] else ''
        return row