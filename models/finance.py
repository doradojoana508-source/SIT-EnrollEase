from db import query


class Finance:
    """Mga datos para sa Finance: pila ng quotation at estado ng bayad."""

    # Hindi kasama ang mga applicant ng term na naka-archive na
    SCOPE = "a.status = 'For Enrollment' AND (t.admission_status IS NULL OR t.admission_status <> 'Archived')"
    FROM = ("FROM applications a JOIN users u ON u.id = a.user_id "
            "LEFT JOIN programs p ON p.id = a.program_id "
            "LEFT JOIN academic_terms t ON t.id = a.term_id "
            "LEFT JOIN quotations qt ON qt.application_id = a.id")

    @classmethod
    def _filters(cls, q='', state=None):
        """state: None = lahat, 'ready' = wala pang quotation, 'quoted' = naghihintay ng bayad, 'paid' = buo na ang bayad."""
        where = [cls.SCOPE, 'a.originals_received_at IS NOT NULL']
        params = []
        if state == 'ready':
            where.append('qt.id IS NULL')
        elif state == 'quoted':
            where.append('qt.id IS NOT NULL AND qt.paid_at IS NULL')
        elif state == 'paid':
            where.append('qt.paid_at IS NOT NULL')
        if q:
            like = f'%{q}%'
            where.append('(u.first_name LIKE %s OR u.last_name LIKE %s OR u.email LIKE %s OR qt.student_id LIKE %s)')
            params += [like, like, like, like]
        return ' AND '.join(where), params

    @classmethod
    def queue_count(cls, q='', state=None):
        where, params = cls._filters(q, state)
        return query(f'SELECT COUNT(*) AS n {cls.FROM} WHERE {where}', params, one=True)['n']

    @classmethod
    def queue(cls, q='', limit=10, offset=0, state=None):
        """Una ang wala pang quotation, sunod ang naghihintay ng bayad, huli ang Paid."""
        where, params = cls._filters(q, state)
        return query(
            'SELECT a.id, a.applicant_type, a.originals_received_at, u.first_name, u.last_name, u.email, '
            'p.code AS program_code, p.name AS program_name, t.term_no, t.academic_year, '
            'qt.id AS quotation_id, qt.student_id, qt.total, qt.paid_at, '
            '(SELECT COALESCE(SUM(pm.amount), 0) FROM payments pm '
            ' WHERE pm.quotation_id = qt.id AND pm.voided_at IS NULL) AS paid '
            f'{cls.FROM} WHERE {where} '
            'ORDER BY (qt.id IS NOT NULL) ASC, (qt.paid_at IS NOT NULL) ASC, '
            'a.originals_received_at ASC, a.id ASC LIMIT %s OFFSET %s',
            params + [limit, offset])

    @classmethod
    def counts(cls):
        waiting = query(f'SELECT COUNT(*) AS n {cls.FROM} WHERE {cls.SCOPE} AND a.originals_received_at IS NULL',
                        (), one=True)['n']
        return {'ready': cls.queue_count(state='ready'), 'quoted': cls.queue_count(state='quoted'),
                'paid': cls.queue_count(state='paid'), 'waiting': waiting}