from decimal import Decimal
from db import query, execute
from models.application import Application
from models.notification import Notification
from models.user import User


class PreEnrollment:
    """Pre-enrollment ng Continuing at Returnee na student. Gumagawa ng application para sa bagong term
    (isang application bawat term), kaya may sarili silang quotation at bayad. Hindi ito puwede kapag may balance."""

    TYPES = ('Continuing', 'Returnee')

    # ---------- mga tanong sa database ----------
    @staticmethod
    def open_term():
        row = query("SELECT * FROM academic_terms WHERE admission_status = 'Open' "
                    "ORDER BY academic_year DESC, term_no DESC LIMIT 1", (), one=True)
        if row:
            row['label'] = f"Trimester {row['term_no']}, {row['academic_year']}"
        return row

    @staticmethod
    def outstanding(user_id):
        """Kabuuang balance sa lahat ng term (kinukuwenta, hindi galing sa form)."""
        row = query(
            "SELECT COALESCE(SUM(q.total), 0) - COALESCE((SELECT SUM(pm.amount) FROM payments pm "
            "JOIN quotations q2 ON q2.id = pm.quotation_id JOIN applications a2 ON a2.id = q2.application_id "
            "WHERE a2.user_id = %s AND pm.voided_at IS NULL), 0) AS n "
            "FROM quotations q JOIN applications a ON a.id = q.application_id WHERE a.user_id = %s",
            (user_id, user_id), one=True)
        return max(row['n'], Decimal('0'))

    @staticmethod
    def latest_application(user_id):
        return query("SELECT * FROM applications WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,), one=True)

    @classmethod
    def program_id(cls, user_id):
        latest = cls.latest_application(user_id)
        if latest and latest['program_id']:
            return latest['program_id']
        row = query("SELECT program_id FROM cors WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,), one=True)
        return row['program_id'] if row else None

    @staticmethod
    def programs():
        return query("SELECT id, code, name FROM programs WHERE is_active = 1 ORDER BY id")

    # ---------- kalagayan ----------
    @classmethod
    def summary(cls, user_id):
        term = cls.open_term()
        out = {'term': term, 'outstanding': cls.outstanding(user_id), 'application': None, 'quotation': None,
               'stage': '', 'state': 'closed', 'program_id': cls.program_id(user_id)}
        out['needs_program'] = out['program_id'] is None
        if term is None:
            return out
        app = query("SELECT * FROM applications WHERE user_id = %s AND term_id = %s", (user_id, term['id']), one=True)
        if app:
            out['application'] = app
            q = query("SELECT * FROM quotations WHERE application_id = %s", (app['id'],), one=True)
            out['quotation'] = q
            if app['status'] == 'Enrolled':
                out['state'], out['stage'] = 'enrolled', 'You are enrolled for this term. See COR & Schedule.'
            else:
                out['state'] = 'pending'
                if q is None:
                    out['stage'] = 'Waiting for the Finance office to prepare your tuition quotation.'
                elif q['paid_at'] is None:
                    out['stage'] = 'Your quotation is ready. Please pay at the Finance office.'
                else:
                    out['stage'] = 'Fully paid. The Registrar will prepare your COR.'
        elif out['outstanding'] > 0:
            out['state'] = 'blocked'
        else:
            out['state'] = 'open'
        return out

    # ---------- pag-submit ----------
    @classmethod
    def create(cls, user, student_type, program_id=None):
        info = cls.summary(user.id)
        term = info['term']
        if info['state'] == 'closed':
            raise ValueError('Enrollment is not open right now.')
        if info['state'] == 'blocked':
            raise ValueError('You still have an unpaid balance. Please settle it with the Finance office first.')
        if info['state'] != 'open':
            raise ValueError('You already pre-enrolled for this term.')
        if student_type not in cls.TYPES:
            raise ValueError('Choose Continuing or Returnee.')
        if query("SELECT id FROM cors WHERE user_id = %s AND term_id = %s", (user.id, term['id']), one=True):
            raise ValueError('You already have a COR for this term.')
        pid = info['program_id']
        if pid is None:
            if program_id not in {p['id'] for p in cls.programs()}:
                raise ValueError('Choose your degree program.')
            pid = program_id

        latest = cls.latest_application(user.id)
        cols = [c for c in Application.FIELDS if c not in ('applicant_type', 'program_id')]
        execute("INSERT INTO applications (user_id, term_id, program_id, applicant_type, status, submitted_at, "
                "originals_received_at" + ''.join(f', {c}' for c in cols) + ") VALUES (%s, %s, %s, %s, "
                "'For Enrollment', NOW(), NOW()" + ', %s' * len(cols) + ")",
                [user.id, term['id'], pid, student_type] + [latest.get(c) if latest else None for c in cols])
        execute("INSERT INTO enrollments (user_id, term_id, student_type, status) VALUES (%s, %s, %s, 'Pre-enrolled') "
                "ON DUPLICATE KEY UPDATE student_type = VALUES(student_type)", (user.id, term['id'], student_type))

        details = [('Student ID', user.username or '-'), ('Type', student_type), ('Term', term['label'])]
        Notification.notify(user, 'Your SIT pre-enrollment', 'Pre-enrollment received',
                            'Your pre-enrollment was received. The Finance office will prepare your tuition '
                            'quotation, and the Registrar will prepare your COR after you pay.', details)
        for row in query("SELECT id FROM users WHERE role = 'finance' AND is_active = 1"):
            staff = User.find(row['id'])
            if staff:
                Notification.notify(staff, 'A student pre-enrolled', 'New pre-enrollment',
                                    f'{user.full_name} pre-enrolled and needs a tuition quotation.', details)
        return term

    @classmethod
    def cancel(cls, user):
        info = cls.summary(user.id)
        app = info['application']
        if app is None or app['status'] != 'For Enrollment' or info['quotation'] is not None:
            raise ValueError('Pre-enrollment can only be cancelled before the Finance office prepares your quotation.')
        execute("DELETE FROM enrollments WHERE user_id = %s AND term_id = %s AND status = 'Pre-enrolled'",
                (user.id, info['term']['id']))
        execute("DELETE FROM applications WHERE id = %s", (app['id'],))