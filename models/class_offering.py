import re
from datetime import datetime, time, timedelta
from db import query, execute
from models.faculty import Faculty
from models.notification import Notification
from models.user import User

SECTION_RE = re.compile(r'^[A-Z0-9]{1,10}$')


class ClassOffering:
    """Ang mga klaseng bukas sa isang term: subject, section, schedule at professor."""

    DAYS = (('M', 'Monday'), ('T', 'Tuesday'), ('W', 'Wednesday'),
            ('TH', 'Thursday'), ('F', 'Friday'), ('S', 'Saturday'))
    STATUSES = ('Tentative', 'Final')
    EARLIEST, LATEST = time(6, 0), time(21, 0)

    # ---------- oras at schedule (format ng COR: TH / 8-10AM) ----------
    @staticmethod
    def as_time(value):
        """Ang TIME ng MySQL ay minsang timedelta."""
        return (datetime.min + value).time() if isinstance(value, timedelta) else value

    @staticmethod
    def _hour(t):
        h = t.hour % 12 or 12
        return f'{h}:{t.minute:02d}' if t.minute else str(h)

    @classmethod
    def range_label(cls, start, end):
        start, end = cls.as_time(start), cls.as_time(end)
        mer = lambda t: 'AM' if t.hour < 12 else 'PM'
        end_noon = (end.hour, end.minute) == (12, 0)
        end_mer = 'AM' if end_noon else mer(end)
        end_text = '12N' if end_noon else cls._hour(end) + mer(end)
        start_text = cls._hour(start) + ('' if mer(start) == end_mer else mer(start))
        return f'{start_text}-{end_text}'

    @classmethod
    def schedule_label(cls, day, start, end):
        return f'{day} / {cls.range_label(start, end)}'

    @classmethod
    def _decorate(cls, row):
        row['schedule'] = cls.schedule_label(row['day_code'], row['start_time'], row['end_time'])
        row['professor'] = None
        if row.get('faculty_id') and row.get('first_name'):
            row['professor'] = Faculty.label({'first_name': row['first_name'], 'title': row.get('f_title'),
                                              'display_name': row.get('display_name')})
        return row

    # ---------- term ----------
    @staticmethod
    def terms():
        rows = query("SELECT id, term_no, academic_year, admission_status, is_current FROM academic_terms "
                     "WHERE admission_status <> 'Archived' ORDER BY academic_year DESC, term_no DESC")
        for r in rows:
            r['label'] = f"Trimester {r['term_no']}, {r['academic_year']}"
        return rows

    @staticmethod
    def pick_term(terms, requested_id=None):
        for t in terms:
            if t['id'] == requested_id:
                return t
        return next((t for t in terms if t['is_current']), terms[0] if terms else None)

    # ---------- mga subject na mapipili ----------
    @staticmethod
    def subject_options():
        """Bawat (code, pamagat, units) sa curriculum, kasama ang mga program na gumagamit."""
        rows = query(
            "SELECT s.id AS subject_id, s.code, c.title, c.units, "
            "GROUP_CONCAT(DISTINCT p.code ORDER BY p.id SEPARATOR ', ') AS programs "
            "FROM curriculum c JOIN subjects s ON s.id = c.subject_id JOIN programs p ON p.id = c.program_id "
            "GROUP BY s.id, s.code, c.title, c.units ORDER BY s.code, c.title")
        for r in rows:
            r['label'] = f"{r['code']} | {r['title']} | {r['units']} units | {r['programs']}"
        return rows

    # ---------- paghahanap ----------
    _SELECT = ("SELECT c.*, s.code, u.first_name, fp.title AS f_title, fp.display_name "
               "FROM classes c JOIN subjects s ON s.id = c.subject_id "
               "LEFT JOIN users u ON u.id = c.faculty_id "
               "LEFT JOIN faculty_profiles fp ON fp.user_id = u.id")

    @classmethod
    def for_term(cls, term_id, q=''):
        where, params = ['c.term_id = %s'], [term_id]
        if q:
            like = f'%{q}%'
            where.append('(s.code LIKE %s OR c.title LIKE %s OR u.first_name LIKE %s OR u.last_name LIKE %s '
                         'OR fp.display_name LIKE %s)')
            params += [like] * 5
        rows = query(f"{cls._SELECT} WHERE {' AND '.join(where)} ORDER BY s.code, c.section, c.id", params)
        return [cls._decorate(r) for r in rows]

    @classmethod
    def find(cls, class_id):
        row = query(f"{cls._SELECT} WHERE c.id = %s", (class_id,), one=True)
        return cls._decorate(row) if row else None

    @classmethod
    def to_form(cls, row):
        return {'section': row['section'], 'day_code': row['day_code'],
                'start_time': cls.as_time(row['start_time']).strftime('%H:%M'),
                'end_time': cls.as_time(row['end_time']).strftime('%H:%M'),
                'faculty_id': str(row['faculty_id'] or ''), 'status': row['status']}

    # ---------- pagsusuri ----------
    @classmethod
    def clean(cls, form, term_id, existing=None):
        """Ibinabalik ang (data, errors). Kapag may existing, hindi na mababago ang subject."""
        data, errors = {}, []
        if existing:
            data.update(subject_id=existing['subject_id'], title=existing['title'], units=existing['units'])
        else:
            pick = form.get('subject_pick', '').strip()
            option = next((o for o in cls.subject_options() if o['label'] == pick), None)
            if option is None:
                errors.append('Choose a subject from the list (type the code or the title).')
            else:
                data.update(subject_id=option['subject_id'], title=option['title'], units=option['units'])

        section = form.get('section', '').strip().upper()
        if not SECTION_RE.match(section):
            errors.append('Section must be letters or numbers, up to 10 characters (for example A).')
        data['section'] = section

        day = form.get('day_code', '')
        if day not in dict(cls.DAYS):
            errors.append('Choose the day.')
        data['day_code'] = day

        times_ok = True
        for key, label in (('start_time', 'start'), ('end_time', 'end')):
            try:
                data[key] = datetime.strptime(form.get(key, '').strip(), '%H:%M').time()
            except ValueError:
                errors.append(f'Enter the {label} time.')
                times_ok = False
        if times_ok and data['end_time'] <= data['start_time']:
            errors.append('The end time must be after the start time.')
            times_ok = False
        elif times_ok and (data['start_time'] < cls.EARLIEST or data['end_time'] > cls.LATEST):
            errors.append('Class time must be between 6:00 AM and 9:00 PM.')
            times_ok = False

        own_id = existing['id'] if existing else 0
        data['faculty_id'] = None
        raw = form.get('faculty_id', '').strip()
        if raw:
            if raw.isdigit() and int(raw) in {f['id'] for f in Faculty.options()}:
                data['faculty_id'] = int(raw)
            else:
                errors.append('Choose a valid professor.')
        if data['faculty_id'] and times_ok and day in dict(cls.DAYS):
            clash = query(
                "SELECT s.code FROM classes c JOIN subjects s ON s.id = c.subject_id "
                "WHERE c.term_id = %s AND c.faculty_id = %s AND c.day_code = %s AND c.id <> %s "
                "AND c.start_time < %s AND c.end_time > %s LIMIT 1",
                (term_id, data['faculty_id'], day, own_id, data['end_time'], data['start_time']), one=True)
            if clash:
                errors.append(f"The professor already teaches {clash['code']} at that time.")

        if 'subject_id' in data and SECTION_RE.match(section):
            dup = query("SELECT id FROM classes WHERE term_id = %s AND subject_id = %s AND title = %s "
                        "AND section = %s AND id <> %s",
                        (term_id, data['subject_id'], data['title'], section, own_id), one=True)
            if dup:
                errors.append('That subject and section is already open this term.')

        status = form.get('status', 'Tentative')
        if status not in cls.STATUSES:
            errors.append('Choose Tentative or Final.')
            status = 'Tentative'
        data['status'] = status
        return data, errors

    # ---------- pag-save ----------
    @classmethod
    def create(cls, term_id, data, by_user):
        class_id = execute(
            "INSERT INTO classes (term_id, subject_id, title, units, section, day_code, start_time, end_time, "
            "faculty_id, status, created_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (term_id, data['subject_id'], data['title'], data['units'], data['section'], data['day_code'],
             data['start_time'], data['end_time'], data['faculty_id'], data['status'], by_user.id))
        cls._notify_assigned(class_id)
        return class_id

    @classmethod
    def update(cls, existing, data):
        execute("UPDATE classes SET section = %s, day_code = %s, start_time = %s, end_time = %s, "
                "faculty_id = %s, status = %s WHERE id = %s",
                (data['section'], data['day_code'], data['start_time'], data['end_time'],
                 data['faculty_id'], data['status'], existing['id']))
        if data['faculty_id'] and data['faculty_id'] != existing['faculty_id']:
            cls._notify_assigned(existing['id'])

    @staticmethod
    def delete(class_id):
        execute("DELETE FROM classes WHERE id = %s", (class_id,))

    @classmethod
    def _notify_assigned(cls, class_id):
        row = cls.find(class_id)
        if not row or not row['faculty_id']:
            return
        teacher = User.find(row['faculty_id'])
        term = query("SELECT term_no, academic_year FROM academic_terms WHERE id = %s", (row['term_id'],), one=True)
        Notification.notify(
            teacher, 'You were assigned a class at SIT', 'New class assignment',
            'The Registrar assigned you to teach a class. The schedule stays tentative until it is marked Final.',
            [('Subject', f"{row['code']} {row['title']}"), ('Section', row['section']),
             ('Schedule', row['schedule']), ('Term', f"Trimester {term['term_no']}, {term['academic_year']}")])