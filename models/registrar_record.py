from db import query, execute


class RegistrarRecord:
    """Student Records ng Registrar: profile, kasaysayan ng enrollment (COR), grades at detalye ng TOR."""

    FROM = ("FROM users u LEFT JOIN applications a ON a.user_id = u.id "
            "LEFT JOIN quotations q ON q.application_id = a.id "
            "LEFT JOIN programs p ON p.id = COALESCE(a.program_id, "
            "(SELECT c2.program_id FROM cors c2 WHERE c2.user_id = u.id ORDER BY c2.id DESC LIMIT 1))")
    SCOPE = "(u.role = 'student' OR a.status = 'Enrolled')"
    SID = "COALESCE(u.username, q.student_id)"
    TOR_FIELDS = ('last_attended', 'category', 'school', 'degree', 'major', 'admitted', 'conferred')

    @staticmethod
    def programs():
        return query("SELECT id, code FROM programs ORDER BY id")

    @classmethod
    def _where(cls, q='', program_id=None):
        where, params = [cls.SCOPE], []
        if program_id:
            where.append('p.id = %s')
            params.append(program_id)
        if q:
            like = f'%{q}%'
            where.append(f'(u.first_name LIKE %s OR u.last_name LIKE %s OR {cls.SID} LIKE %s)')
            params += [like] * 3
        return ' AND '.join(where), params

    @classmethod
    def count(cls, q='', program_id=None):
        where, params = cls._where(q, program_id)
        return query(f'SELECT COUNT(DISTINCT u.id) AS n {cls.FROM} WHERE {where}', params, one=True)['n']

    @classmethod
    def rows(cls, q='', program_id=None, limit=10, offset=0):
        where, params = cls._where(q, program_id)
        rows = query(
            f'SELECT u.id AS user_id, u.first_name, u.middle_name, u.last_name, u.role, {cls.SID} AS student_id, '
            'p.code AS program_code, p.name AS program_name, '
            '(SELECT COUNT(*) FROM grades g WHERE g.user_id = u.id) AS grade_count '
            f'{cls.FROM} WHERE {where} GROUP BY u.id ORDER BY u.last_name, u.first_name LIMIT %s OFFSET %s',
            params + [limit, offset])
        for r in rows:
            r['name'] = cls.formal_name(r)
        return rows

    @staticmethod
    def formal_name(row):
        middle = f" {row['middle_name'][0].upper()}." if row.get('middle_name') else ''
        return f"{row['last_name'].upper()}, {row['first_name'].upper()}{middle}"

    @classmethod
    def find(cls, user_id):
        row = query(
            f'SELECT u.id AS user_id, u.email, u.role, u.first_name, u.middle_name, u.last_name, {cls.SID} AS student_id, '
            'p.code AS program_code, p.name AS program_name, a.birthdate, a.birthplace, a.gender, a.civil_status, '
            f'a.nationality, a.phone, a.address {cls.FROM} WHERE u.id = %s AND {cls.SCOPE} LIMIT 1',
            (user_id,), one=True)
        if row:
            row['name'] = cls.formal_name(row)
        return row

    @staticmethod
    def cors(user_id):
        rows = query(
            "SELECT c.id, c.term_id, c.year_level, c.status, t.term_no, t.academic_year, "
            "(SELECT COALESCE(SUM(cl.units), 0) FROM cor_subjects cs JOIN classes cl ON cl.id = cs.class_id "
            "WHERE cs.cor_id = c.id) AS units FROM cors c JOIN academic_terms t ON t.id = c.term_id "
            "WHERE c.user_id = %s ORDER BY t.academic_year DESC, t.term_no DESC", (user_id,))
        return rows

    # ---------- detalye ng TOR ----------
    @classmethod
    def tor_info(cls, user_id):
        row = query("SELECT * FROM tor_info WHERE user_id = %s", (user_id,), one=True) or {}
        return {k: row.get(k) or '' for k in cls.TOR_FIELDS}

    @classmethod
    def save_tor_info(cls, user_id, form):
        values = [form.get(k, '').strip()[:120] or None for k in cls.TOR_FIELDS]
        execute("INSERT INTO tor_info (user_id, last_attended, category, school, degree, major, admitted, conferred) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE last_attended = VALUES(last_attended), "
                "category = VALUES(category), school = VALUES(school), degree = VALUES(degree), "
                "major = VALUES(major), admitted = VALUES(admitted), conferred = VALUES(conferred)",
                [user_id] + values)