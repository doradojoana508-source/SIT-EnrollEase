import re
from datetime import date
from decimal import Decimal
from db import query, execute
from models.class_offering import ClassOffering
from models.scheduler import Scheduler
from models.notification import Notification
from models.user import User

SCHOLAR_RE = re.compile(r"^[\w\s.,;&/()'%\-]{0,80}$", re.UNICODE)
ORDINAL = {1: '1st', 2: '2nd', 3: '3rd'}
WORD = {1: 'FIRST', 2: 'SECOND', 3: 'THIRD'}


class Cor:
    """Certificate of Registration: awtomatikong gawa ng system, tentative, at ine-edit ng Registrar.
    Ang mga subject ay nakakabit sa mga klase, kaya kapag nagbago ang schedule o professor, nagbabago rin ang COR."""

    YEARS = ('1st', '2nd', '3rd', '4th')

    _STUDENT = (
        "SELECT a.id AS application_id, a.user_id, a.program_id, a.applicant_type, "
        "u.first_name, u.middle_name, u.last_name, u.email, "
        "p.code AS program_code, p.name AS program_name, "
        "q.student_id, q.units AS quoted_units, q.paid_at, c.id AS cor_id, c.status AS cor_status "
        "FROM applications a JOIN users u ON u.id = a.user_id JOIN programs p ON p.id = a.program_id "
        "JOIN quotations q ON q.application_id = a.id "
        "LEFT JOIN cors c ON c.user_id = a.user_id AND c.term_id = a.term_id "
        "WHERE a.term_id = %s AND q.paid_at IS NOT NULL")

    # ---------- pagpapakita ----------
    @staticmethod
    def formal_name(row):
        middle = f" {row['middle_name'][0].upper()}." if row.get('middle_name') else ''
        return f"{row['last_name'].upper()}, {row['first_name'].upper()}{middle}"

    @staticmethod
    def heading(term):
        n = term['term_no']
        return f"{WORD[n]} ({ORDINAL[n]}) Trimester, A.Y. {term['academic_year']}"

    @staticmethod
    def trimester_label(term):
        return f"{ORDINAL[term['term_no']]}, AY.: {term['academic_year']}"

    # ---------- mga student na Paid ----------
    @classmethod
    def paid_students(cls, term_id, q=''):
        sql, params = cls._STUDENT, [term_id]
        if q:
            like = f'%{q}%'
            sql += " AND (u.first_name LIKE %s OR u.last_name LIKE %s OR q.student_id LIKE %s)"
            params += [like, like, like]
        rows = query(sql + " ORDER BY u.last_name, u.first_name", params)
        for r in rows:
            r['name'] = cls.formal_name(r)
            r['units_label'] = format(r['quoted_units'].normalize(), 'f')
        return rows

    @classmethod
    def student(cls, user_id, term_id):
        row = query(cls._STUDENT + " AND a.user_id = %s", (term_id, user_id), one=True)
        if row:
            row['name'] = cls.formal_name(row)
        return row

    # ---------- ang COR ----------
    @classmethod
    def load(cls, user_id, term_id):
        cor = query("SELECT * FROM cors WHERE user_id = %s AND term_id = %s", (user_id, term_id), one=True)
        if cor is None:
            return None
        rows = query(
            "SELECT cs.id AS cs_id, cl.id AS class_id, cl.subject_id, cl.title, cl.units, cl.section, "
            "cl.day_code, cl.start_time, cl.end_time, cl.faculty_id, s.code, u.first_name, "
            "fp.title AS f_title, fp.display_name "
            "FROM cor_subjects cs JOIN classes cl ON cl.id = cs.class_id JOIN subjects s ON s.id = cl.subject_id "
            "LEFT JOIN users u ON u.id = cl.faculty_id LEFT JOIN faculty_profiles fp ON fp.user_id = u.id "
            "WHERE cs.cor_id = %s ORDER BY cs.id", (cor['id'],))
        cor['subjects'] = [ClassOffering._decorate(r) for r in rows]
        cor['total_units'] = sum(r['units'] for r in cor['subjects'])
        return cor

    @staticmethod
    def to_form(cor):
        return {'year_level': cor['year_level'], 'scholarship': cor['scholarship'] or '',
                'date_enrolled': cor['date_enrolled'].isoformat() if cor['date_enrolled'] else ''}

    @classmethod
    def add_options(cls, cor, student, term_id):
        """Mga klaseng puwedeng idagdag: yung hindi pa nasa COR. Una ang mga nasa curriculum ng program niya."""
        have = {s['subject_id'] for s in cor['subjects']}
        in_program = {(r['subject_id'], r['title']) for r in
                      query("SELECT subject_id, title FROM curriculum WHERE program_id = %s", (student['program_id'],))}
        mine, others = [], []
        for c in ClassOffering.for_term(term_id):
            if c['subject_id'] in have:
                continue
            c['label'] = (f"{c['code']} | {c['title']} | {c['units']}u | {c['schedule']} | "
                          f"{c['professor'] or 'no professor'}")
            (mine if (c['subject_id'], c['title']) in in_program else others).append(c)
        return mine, others

    # ---------- pag-iwas sa magkapatong na oras ----------
    @staticmethod
    def _overlap(a, b):
        return a['day_code'] == b['day_code'] and a['start_time'] < b['end_time'] and a['end_time'] > b['start_time']

    @classmethod
    def conflicts(cls, rows):
        msgs = []
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                if cls._overlap(a, b):
                    msgs.append(f"{a['code']} ({a['schedule']}) and {b['code']} ({b['schedule']}) overlap.")
        return msgs

    # ---------- awtomatikong pagpuno ----------
    @classmethod
    def suggest(cls, student, term_id):
        """Sundan ang curriculum ng program (ayon sa seq), hanggang sa units na naka-quote at hanggang sa mga slot
        ng Huwebes. Gagamit ng klaseng bukas na, o gagawa ang system ng bago (Huwebes, may professor ayon sa
        specialty). Lalaktawan ang mga subject na nakuha na sa ibang term."""
        cap = Decimal(student['quoted_units'])
        done = {r['subject_id'] for r in query(
            "SELECT cl.subject_id FROM cor_subjects cs JOIN cors c ON c.id = cs.cor_id "
            "JOIN classes cl ON cl.id = cs.class_id WHERE c.user_id = %s AND c.term_id <> %s",
            (student['user_id'], term_id))}
        curriculum = query("SELECT subject_id, title, units FROM curriculum WHERE program_id = %s ORDER BY seq",
                           (student['program_id'],))
        picked, units = [], Decimal('0')
        for item in curriculum:
            if len(picked) >= len(Scheduler.SLOTS):
                break
            if item['subject_id'] in done or units + item['units'] > cap:
                continue
            row = Scheduler.place(term_id, item, picked)
            if row is not None:
                picked.append(row)
                units += item['units']
        return picked

    @classmethod
    def generate(cls, student, term, by_user):
        """Gumagawa ng tentative COR, ginagawang Enrolled ang student, at nag-aabiso sa Admin at mga professor."""
        if cls.load(student['user_id'], term['id']):
            raise ValueError('This student already has a COR for this term.')
        classes = cls.suggest(student, term['id'])
        cor_id = execute(
            "INSERT INTO cors (user_id, term_id, program_id, year_level, date_enrolled, status, created_by) "
            "VALUES (%s, %s, %s, '1st', CURDATE(), 'Tentative', %s)",
            (student['user_id'], term['id'], student['program_id'], by_user.id))
        for c in classes:
            execute("INSERT INTO cor_subjects (cor_id, class_id) VALUES (%s, %s)", (cor_id, c['id']))
        execute("INSERT INTO enrollments (user_id, term_id, student_type, status, enrolled_at) "
                "VALUES (%s, %s, %s, 'Enrolled', NOW()) "
                "ON DUPLICATE KEY UPDATE status = 'Enrolled', enrolled_at = COALESCE(enrolled_at, NOW())",
                (student['user_id'], term['id'], student['applicant_type']))
        execute("UPDATE applications SET status = 'Enrolled' WHERE id = %s", (student['application_id'],))

        owner = User.find(student['user_id'])
        Notification.notify(
            owner, 'Your SIT Certificate of Registration', 'You are now enrolled',
            'Your Certificate of Registration was prepared by the Registrar. It is tentative and may still change. '
            'The school will send your student account activation link.',
            [('Student ID', student['student_id']), ('Program', student['program_name']),
             ('Term', f"Trimester {term['term_no']}, {term['academic_year']}")])
        for admin in query("SELECT id FROM users WHERE role = 'admin' AND is_active = 1"):
            Notification.notify(
                User.find(admin['id']), 'A new student needs an account', 'Student account needed',
                f"{student['name']} is now enrolled. Please create the student account under Pending Students.",
                [('Student ID', student['student_id']), ('Program', student['program_code'])])
        cls._notify_professors(student['name'], [c['id'] for c in classes])
        return len(classes)

    @classmethod
    def regenerate(cls, cor, student, term):
        """Papalitan ang lahat ng subject ng bagong auto-fill."""
        execute("DELETE FROM cor_subjects WHERE cor_id = %s", (cor['id'],))
        classes = cls.suggest(student, term['id'])
        for c in classes:
            execute("INSERT INTO cor_subjects (cor_id, class_id) VALUES (%s, %s)", (cor['id'], c['id']))
        cls._notify_professors(student['name'], [c['id'] for c in classes])
        return len(classes)

    @staticmethod
    def _notify_professors(student_label, class_ids):
        """Isang abiso bawat professor, kasama ang mga klase niya."""
        by_prof = {}
        for class_id in class_ids:
            row = ClassOffering.find(class_id)
            if row and row['faculty_id']:
                by_prof.setdefault(row['faculty_id'], []).append(row)
        for faculty_id, rows in by_prof.items():
            teacher = User.find(faculty_id)
            if teacher is None:
                continue
            Notification.notify(
                teacher, 'A student enrolled in your class', 'New student in your class',
                f'{student_label} was enrolled in your class.',
                [(f"{r['code']} {r['title']}", r['schedule']) for r in rows])

    # ---------- pag-edit ng Registrar ----------
    @classmethod
    def save(cls, cor, student, form, action, by_user):
        """Ibinabalik ang listahan ng errors. Walang error = na-save na."""
        errors = []
        year = form.get('year_level', '')
        if year not in cls.YEARS:
            errors.append('Choose the year level.')
        scholarship = ' '.join(form.get('scholarship', '').split())
        if not SCHOLAR_RE.match(scholarship):
            errors.append('Scholarship has invalid characters or is too long (80 characters maximum).')
        enrolled_on = None
        try:
            enrolled_on = date.fromisoformat(form.get('date_enrolled', '').strip())
        except ValueError:
            errors.append('Enter a valid Date Enrolled.')

        remove = {int(x) for x in form.getlist('remove') if x.isdigit()}
        kept = [s for s in cor['subjects'] if s['cs_id'] not in remove]
        added = None
        raw = form.get('add_class', '').strip()
        if raw:
            added = ClassOffering.find(int(raw)) if raw.isdigit() else None
            if added is None or added['term_id'] != cor['term_id']:
                errors.append('Choose a valid class to add.')
                added = None
            elif added['subject_id'] in {s['subject_id'] for s in kept}:
                errors.append(f"{added['code']} is already in this COR.")
                added = None
        rows = kept + ([added] if added else [])
        errors += cls.conflicts(rows)

        if action == 'final':
            if not rows:
                errors.append('Add at least one subject before marking the COR Final.')
            missing = [r['code'] for r in rows if not r['faculty_id']]
            if missing:
                errors.append('These subjects still have no professor: ' + ', '.join(missing) + '.')
        if errors:
            return errors

        for cs_id in remove:
            execute("DELETE FROM cor_subjects WHERE id = %s AND cor_id = %s", (cs_id, cor['id']))
        if added:
            execute("INSERT INTO cor_subjects (cor_id, class_id) VALUES (%s, %s)", (cor['id'], added['id']))
        status = {'final': 'Final', 'tentative': 'Tentative'}.get(action, cor['status'])
        execute("UPDATE cors SET year_level = %s, scholarship = %s, date_enrolled = %s, status = %s WHERE id = %s",
                (year, scholarship or None, enrolled_on, status, cor['id']))
        if added:
            cls._notify_professors(student['name'], [added['id']])
        if status == 'Final' and cor['status'] != 'Final':
            Notification.notify(
                User.find(student['user_id']), 'Your SIT COR is final', 'Certificate of Registration is final',
                'The Registrar confirmed your Certificate of Registration.',
                [('Student ID', student['student_id']), ('Year', year), ('Total units', str(sum(r['units'] for r in rows)))])
        return []