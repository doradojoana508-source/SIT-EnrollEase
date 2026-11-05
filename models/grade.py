import re
from db import query, execute
from models.class_offering import ClassOffering


class Grade:
    """Mga grade ng student. Isang row = isang subject sa isang term. Puwedeng galing sa klase (faculty) o
    manu-manong nilagay ng Registrar (mga lumang record)."""

    GRADES = ('1.00', '1.25', '1.50', '1.75', '2.00', '2.25', '2.50', '2.75', '3.00',
              '5.00', 'INC', 'DRP', '5A', '5W')
    TERM_NAMES = {1: '1st Trimester', 2: '2nd Trimester', 3: '3rd Trimester', 4: 'Special Trimester'}
    SHORT = {1: '1st', 2: '2nd', 3: '3rd', 4: 'Special'}
    SCALE = (('1.00', '98% and above'), ('1.25', '95-97%'), ('1.50', '92-94%'), ('1.75', '89-91%'),
             ('2.00', '86-88%'), ('2.25', '83-85%'), ('2.50', '80-82%'), ('2.75', '77-79%'),
             ('3.00', '75-76%'), ('5.00', 'below 75% Failed'))
    OTHER = (('INC', 'Incomplete'), ('DRP', 'Dropped'), ('5A', 'Failure'), ('5W', 'Withdrawal'))
    AY_RE = re.compile(r'^(\d{4})-(\d{4})$')
    CODE_RE = re.compile(r'^[A-Za-z0-9 .\-]{1,20}$')
    TITLE_RE = re.compile(r"^[\w\s.,:;&/()'\-]{2,120}$", re.UNICODE)

    # ---------- pagpapakita ----------
    @staticmethod
    def remark(grade):
        if grade in ('1.00', '1.25', '1.50', '1.75', '2.00', '2.25', '2.50', '2.75', '3.00'):
            return 'PASSED'
        return {'5.00': 'FAILED', '5A': 'FAILED', 'INC': 'INCOMPLETE', 'DRP': 'DROPPED', '5W': 'WITHDRAWN'}.get(grade, '')

    @classmethod
    def term_label(cls, term_no, academic_year):
        return f'{cls.TERM_NAMES[term_no]}, {academic_year}'

    @classmethod
    def short_ay(cls, academic_year):
        a, b = academic_year.split('-')
        return f'{a[2:]}-{b[2:]}'

    @classmethod
    def for_student(cls, user_id):
        rows = query("SELECT * FROM grades WHERE user_id = %s ORDER BY academic_year, term_no, id", (user_id,))
        for r in rows:
            r['remark'] = cls.remark(r['grade'])
        return rows

    @classmethod
    def grouped(cls, rows):
        """Pinagsama-sama bawat term: [{'tn', 'ay', 'label', 'rows', 'units'}]."""
        groups = {}
        for r in rows:
            key = (r['academic_year'], r['term_no'])
            if key not in groups:
                groups[key] = {'tn': r['term_no'], 'ay': r['academic_year'],
                               'label': cls.term_label(r['term_no'], r['academic_year']), 'rows': [], 'units': 0}
            groups[key]['rows'].append(r)
            groups[key]['units'] += r['units']
        return list(groups.values())

    @staticmethod
    def find(grade_id, user_id):
        return query("SELECT * FROM grades WHERE id = %s AND user_id = %s", (grade_id, user_id), one=True)

    @staticmethod
    def to_form(row):
        return {'term_no': str(row['term_no']), 'academic_year': row['academic_year'], 'code': row['code'],
                'title': row['title'], 'units': str(row['units']), 'grade': row['grade'],
                'removal': row['removal_rating'] or ''}

    # ---------- pagsusuri ----------
    @classmethod
    def clean(cls, form, user_id, existing=None):
        data, errors = {}, []
        raw = form.get('term_no', '')
        if raw.isdigit() and int(raw) in cls.TERM_NAMES:
            data['term_no'] = int(raw)
        else:
            errors.append('Choose the trimester.')
        ay = form.get('academic_year', '').strip()
        m = cls.AY_RE.match(ay)
        if m and int(m.group(2)) == int(m.group(1)) + 1:
            data['academic_year'] = ay
        else:
            errors.append('Academic year must look like 2026-2027.')

        pick = form.get('subject_pick', '').strip()
        option = next((o for o in ClassOffering.subject_options() if o['label'] == pick), None) if pick else None
        if option:
            data.update(code=option['code'], title=option['title'], units=int(option['units']))
        else:
            code, title, units = (form.get(k, '').strip() for k in ('code', 'title', 'units'))
            if not cls.CODE_RE.match(code):
                errors.append('Enter the course code (letters, numbers, spaces).')
            if not cls.TITLE_RE.match(title):
                errors.append('Enter the descriptive title (2 to 120 characters).')
            if not (units.isdigit() and 1 <= int(units) <= 12):
                errors.append('Units must be a whole number from 1 to 12.')
            if not errors:
                data.update(code=code, title=title, units=int(units))

        grade = form.get('grade', '')
        if grade not in cls.GRADES:
            errors.append('Choose a grade.')
        data['grade'] = grade
        removal = form.get('removal', '')
        if removal and removal not in cls.GRADES:
            errors.append('Choose a valid removal rating.')
        data['removal'] = removal or None

        if not errors:
            own = existing['id'] if existing else 0
            dup = query("SELECT id FROM grades WHERE user_id = %s AND academic_year = %s AND term_no = %s "
                        "AND code = %s AND id <> %s",
                        (user_id, data['academic_year'], data['term_no'], data['code'], own), one=True)
            if dup:
                errors.append(f"{data['code']} already has a grade in that term. Edit it instead.")
        return data, errors

    # ---------- pag-save ----------
    @staticmethod
    def create(user_id, data, by_user):
        return execute(
            "INSERT INTO grades (user_id, term_no, academic_year, code, title, units, grade, removal_rating, updated_by) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (user_id, data['term_no'], data['academic_year'], data['code'], data['title'], data['units'],
             data['grade'], data['removal'], by_user.id))

    @staticmethod
    def update(grade_id, data, by_user):
        execute("UPDATE grades SET term_no = %s, academic_year = %s, code = %s, title = %s, units = %s, grade = %s, "
                "removal_rating = %s, updated_by = %s WHERE id = %s",
                (data['term_no'], data['academic_year'], data['code'], data['title'], data['units'], data['grade'],
                 data['removal'], by_user.id, grade_id))

    @staticmethod
    def delete(grade_id):
        execute("DELETE FROM grades WHERE id = %s", (grade_id,))