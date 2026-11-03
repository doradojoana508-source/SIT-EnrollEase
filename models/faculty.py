import re
from db import query, execute

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{0,39}$")
SPECIALTY_RE = re.compile(r"^[\w\s.,;&/()'\-]{0,255}$", re.UNICODE)


class Faculty:
    """Mga professor. Ang account ay gawa ng Admin; ang profile ay hawak ng Registrar."""

    TITLES = ('', 'Dr.', 'Rev.', 'Ptr.', 'Prof.', 'Bro.', 'Mr.', 'Mrs.', 'Ms.')
    SELECT = ("SELECT u.id, u.first_name, u.last_name, u.email, u.is_active, u.is_activated, "
              "fp.title, fp.display_name, fp.specialties, "
              "(SELECT COUNT(*) FROM classes c WHERE c.faculty_id = u.id) AS class_count "
              "FROM users u LEFT JOIN faculty_profiles fp ON fp.user_id = u.id WHERE u.role = 'faculty'")

    @staticmethod
    def label(row):
        """Ang pangalan sa COR: ang Display name, o Title + unang pangalan (hal. Dr. Jon)."""
        if row.get('display_name'):
            return row['display_name']
        return f"{row.get('title') or ''} {row['first_name']}".strip()

    @classmethod
    def all(cls):
        rows = query(cls.SELECT + " ORDER BY u.last_name, u.first_name")
        for r in rows:
            r['label'] = cls.label(r)
        return rows

    @classmethod
    def find(cls, user_id):
        row = query(cls.SELECT + " AND u.id = %s", (user_id,), one=True)
        if row:
            row['label'] = cls.label(row)
        return row

    @classmethod
    def options(cls):
        """Mga puwedeng i-assign sa klase: active na faculty."""
        return [r for r in cls.all() if r['is_active']]

    # ---------- awtomatikong pagpili ng professor ----------
    @staticmethod
    def _words(text):
        """Maliliit na titik, walang bantas, at iisahin ang maramihan (Missions = Mission)."""
        words = re.findall(r'[a-z0-9]+', (text or '').lower())
        return [w[:-1] if len(w) > 3 and w.endswith('s') else w for w in words]

    @classmethod
    def matches(cls, specialties, title):
        """Tugma kapag ang lahat ng salita ng isang specialty ay nasa pamagat ng subject."""
        title_words = set(cls._words(title))
        for phrase in (specialties or '').split(','):
            words = cls._words(phrase)
            if words and all(w in title_words for w in words):
                return True
        return False

    @classmethod
    def pick(cls, title, term_id, day, start, end):
        """Ang id ng pinakaangkop na professor: tugma ang specialty, walang klase sa oras na iyon, at
        pinakakaunti ang klase sa term. Ibinabalik ang None kung wala."""
        best, best_load = None, None
        for f in cls.options():
            if not cls.matches(f['specialties'], title):
                continue
            busy = query("SELECT 1 FROM classes WHERE term_id = %s AND faculty_id = %s AND day_code = %s "
                         "AND start_time < %s AND end_time > %s LIMIT 1", (term_id, f['id'], day, end, start), one=True)
            if busy:
                continue
            load = query("SELECT COUNT(*) AS n FROM classes WHERE term_id = %s AND faculty_id = %s",
                         (term_id, f['id']), one=True)['n']
            if best is None or load < best_load:
                best, best_load = f['id'], load
        return best

    @classmethod
    def clean(cls, form):
        data, errors = {}, []
        title = form.get('title', '').strip()
        if title not in cls.TITLES:
            errors.append('Choose a valid title.')
            title = ''
        data['title'] = title

        display = ' '.join(form.get('display_name', '').split())
        if display and not NAME_RE.match(display):
            errors.append('The name on the COR may only contain letters, spaces, periods and hyphens (40 characters maximum).')
        data['display_name'] = display or None

        specialties = ' '.join(form.get('specialties', '').split())
        if not SPECIALTY_RE.match(specialties):
            errors.append('Specialties have invalid characters or are too long (255 characters maximum).')
        data['specialties'] = specialties or None
        return data, errors

    @staticmethod
    def save(user_id, data):
        execute("INSERT INTO faculty_profiles (user_id, title, display_name, specialties) VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE title = VALUES(title), display_name = VALUES(display_name), "
                "specialties = VALUES(specialties)",
                (user_id, data['title'], data['display_name'], data['specialties']))