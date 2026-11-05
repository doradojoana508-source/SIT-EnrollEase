from datetime import date, datetime
from db import query, execute
from models.class_offering import ClassOffering
from models.grade import Grade
from models.notification import Notification
from models.user import User


class Teaching:
    """Para sa professor: mga klase niya, listahan ng student, pag-encode ng grade at attendance."""

    STATUSES = (('P', 'Present'), ('A', 'Absent'), ('L', 'Late'), ('E', 'Excused'))

    # ---------- klase at student ----------
    @staticmethod
    def classes(faculty_id, term_id):
        rows = query(f"{ClassOffering._SELECT} WHERE c.term_id = %s AND c.faculty_id = %s "
                     "ORDER BY c.day_code, c.start_time, s.code", (term_id, faculty_id))
        return [ClassOffering._decorate(r) for r in rows]

    @staticmethod
    def mine(class_id, faculty_id):
        """Ang klase, kung ito ay sa professor na ito lang."""
        row = ClassOffering.find(class_id)
        return row if row and row['faculty_id'] == faculty_id else None

    @staticmethod
    def term(term_id):
        row = query("SELECT * FROM academic_terms WHERE id = %s", (term_id,), one=True)
        row['label'] = Grade.term_label(row['term_no'], row['academic_year'])
        return row

    @staticmethod
    def roster(class_row, term):
        rows = query(
            "SELECT u.id AS user_id, u.first_name, u.middle_name, u.last_name, "
            "COALESCE(u.username, q.student_id) AS student_id, g.grade, g.removal_rating "
            "FROM cor_subjects cs JOIN cors c ON c.id = cs.cor_id JOIN users u ON u.id = c.user_id "
            "LEFT JOIN applications a ON a.user_id = u.id AND a.term_id = %s "
            "LEFT JOIN quotations q ON q.application_id = a.id "
            "LEFT JOIN grades g ON g.user_id = u.id AND g.academic_year = %s AND g.term_no = %s AND g.code = %s "
            "WHERE cs.class_id = %s ORDER BY u.last_name, u.first_name",
            (term['id'], term['academic_year'], term['term_no'], class_row['code'], class_row['id']))
        for r in rows:
            middle = f" {r['middle_name'][0].upper()}." if r['middle_name'] else ''
            r['name'] = f"{r['last_name'].upper()}, {r['first_name'].upper()}{middle}"
            r['remark'] = Grade.remark(r['grade']) if r['grade'] else ''
        return rows

    # ---------- grades ----------
    @staticmethod
    def save_grades(class_row, term, roster, form, by_user):
        """Ibinabalik ang (bilang na na-save, errors). Ang blangkong grade ay lalaktawan."""
        errors, changed = [], []
        for s in roster:
            uid = s['user_id']
            grade = form.get(f'grade_{uid}', '').strip()
            removal = form.get(f'removal_{uid}', '').strip()
            if not grade:
                if removal:
                    errors.append(f"{s['name']}: choose the final grade before the removal rating.")
                continue
            if grade not in Grade.GRADES or (removal and removal not in Grade.GRADES):
                errors.append(f"{s['name']}: invalid grade.")
                continue
            if grade == (s['grade'] or '') and (removal or None) == s['removal_rating']:
                continue
            execute(
                "INSERT INTO grades (user_id, class_id, term_no, academic_year, code, title, units, grade, "
                "removal_rating, updated_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE class_id = VALUES(class_id), title = VALUES(title), units = VALUES(units), "
                "grade = VALUES(grade), removal_rating = VALUES(removal_rating), updated_by = VALUES(updated_by)",
                (uid, class_row['id'], term['term_no'], term['academic_year'], class_row['code'],
                 class_row['title'], class_row['units'], grade, removal or None, by_user.id))
            changed.append((uid, grade))
        for uid, grade in changed:
            student = User.find(uid)
            if student:
                Notification.notify(
                    student, 'A grade was posted at SIT', 'New grade posted',
                    'Your professor posted a grade. You can see it under Grades in the Student Portal.',
                    [('Subject', f"{class_row['code']} {class_row['title']}"), ('Grade', grade)])
        return len(changed), errors

    # ---------- attendance ----------
    @staticmethod
    def parse_date(raw):
        try:
            d = datetime.strptime(raw or '', '%Y-%m-%d').date()
        except ValueError:
            return None
        return d if d <= date.today() else None

    @staticmethod
    def day(class_id, meeting_date):
        rows = query("SELECT user_id, status FROM attendance WHERE class_id = %s AND meeting_date = %s",
                     (class_id, meeting_date))
        return {r['user_id']: r['status'] for r in rows}

    @classmethod
    def save_day(cls, class_id, meeting_date, roster, form, by_user):
        codes = {c for c, _ in cls.STATUSES}
        saved = 0
        for s in roster:
            status = form.get(f"att_{s['user_id']}", '')
            if status in codes:
                execute("INSERT INTO attendance (class_id, user_id, meeting_date, status, recorded_by) "
                        "VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE status = VALUES(status), "
                        "recorded_by = VALUES(recorded_by)",
                        (class_id, s['user_id'], meeting_date, status, by_user.id))
                saved += 1
        return saved

    @staticmethod
    def dates(class_id):
        return [r['meeting_date'] for r in query(
            "SELECT DISTINCT meeting_date FROM attendance WHERE class_id = %s ORDER BY meeting_date DESC", (class_id,))]

    @staticmethod
    def _counts(row):
        for k in ('p', 'a', 'l', 'e', 'total'):
            row[k] = int(row[k] or 0)
        counted = row['total'] - row['e']
        row['rate'] = round((row['p'] + row['l']) * 100 / counted) if counted > 0 else None
        return row

    @classmethod
    def summary(cls, class_id):
        rows = query("SELECT user_id, SUM(status = 'P') AS p, SUM(status = 'A') AS a, SUM(status = 'L') AS l, "
                     "SUM(status = 'E') AS e, COUNT(*) AS total FROM attendance WHERE class_id = %s GROUP BY user_id",
                     (class_id,))
        return {r['user_id']: cls._counts(r) for r in rows}

    @classmethod
    def student_summary(cls, user_id):
        rows = query(
            "SELECT cl.id AS class_id, s.code, cl.title, t.term_no, t.academic_year, SUM(a.status = 'P') AS p, "
            "SUM(a.status = 'A') AS a, SUM(a.status = 'L') AS l, SUM(a.status = 'E') AS e, COUNT(*) AS total "
            "FROM attendance a JOIN classes cl ON cl.id = a.class_id JOIN subjects s ON s.id = cl.subject_id "
            "JOIN academic_terms t ON t.id = cl.term_id WHERE a.user_id = %s GROUP BY cl.id, s.code, cl.title, "
            "t.term_no, t.academic_year ORDER BY t.academic_year DESC, t.term_no DESC, s.code", (user_id,))
        for r in rows:
            cls._counts(r)
            r['term'] = Grade.term_label(r['term_no'], r['academic_year'])
        return rows