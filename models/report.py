import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from db import query
from models.term import Term

TERM_LABEL = "CONCAT('Trimester ', t.term_no, ', A.Y. ', t.academic_year)"
APPLICATION_STATUSES = ('Submitted', 'Approved', 'Interview Scheduled', 'For Enrollment', 'Enrolled',
                        'Rejected', 'Withdrawn')
ROLE_CHOICES = (('', 'All roles'), ('student', 'Students'), ('applicant', 'Applicants'), ('faculty', 'Faculty'),
                ('registrar', 'Registrar'), ('finance', 'Finance'), ('admin', 'Administrators'))


class Spec:
    """Isang report: pamagat, mga filter, mga column ng CSV, at ang SQL."""

    def __init__(self, key, title, about, columns, build, filters=(), after=None):
        self.key, self.title, self.about = key, title, about
        self.columns = columns            # [(header, key sa row)]
        self.filters = list(filters)      # [(name, label, kind, choices)]. kind: term | select | date
        self.build = build                # (filters) -> (sql, params)
        self.after = after                # (rows, filters) -> rows


def _term_filter():
    return ('term', 'Trimester', 'term', None)


def _applications(f):
    where, params = ["a.status <> 'Draft'"], []
    if f['term']:
        where.append('a.term_id = %s')
        params.append(f['term'])
    if f['status']:
        where.append('a.status = %s')
        params.append(f['status'])
    return ("SELECT a.id AS app_id, u.last_name, u.first_name, u.email, p.code AS program, a.applicant_type, "
            f"{TERM_LABEL} AS term, a.status, a.submitted_at, a.originals_received_at "
            "FROM applications a JOIN users u ON u.id = a.user_id "
            "LEFT JOIN programs p ON p.id = a.program_id LEFT JOIN academic_terms t ON t.id = a.term_id "
            f"WHERE {' AND '.join(where)} ORDER BY t.academic_year, t.term_no, u.last_name, u.first_name", params)


def _enrolled(f):
    where, params = ["e.status = 'Enrolled'"], []
    if f['term']:
        where.append('e.term_id = %s')
        params.append(f['term'])
    return ("SELECT COALESCE(u.username, q.student_id) AS student_id, u.last_name, u.first_name, u.middle_name, "
            "p.code AS program, c.year_level, e.student_type, "
            "(SELECT COALESCE(SUM(cl.units), 0) FROM cor_subjects cs JOIN classes cl ON cl.id = cs.class_id "
            " WHERE cs.cor_id = c.id) AS units, c.status AS cor_status, e.enrolled_at, "
            f"{TERM_LABEL} AS term "
            "FROM enrollments e JOIN users u ON u.id = e.user_id JOIN academic_terms t ON t.id = e.term_id "
            "LEFT JOIN cors c ON c.user_id = e.user_id AND c.term_id = e.term_id "
            "LEFT JOIN programs p ON p.id = c.program_id "
            "LEFT JOIN applications a ON a.user_id = e.user_id AND a.term_id = e.term_id "
            "LEFT JOIN quotations q ON q.application_id = a.id "
            f"WHERE {' AND '.join(where)} ORDER BY t.academic_year, t.term_no, u.last_name, u.first_name", params)


def _classes(f):
    where, params = ['1 = 1'], []
    if f['term']:
        where.append('cl.term_id = %s')
        params.append(f['term'])
    return ("SELECT s.code, cl.title, cl.units, "
            "CASE cl.day_code WHEN 'M' THEN 'Monday' WHEN 'T' THEN 'Tuesday' WHEN 'W' THEN 'Wednesday' "
            "WHEN 'TH' THEN 'Thursday' WHEN 'F' THEN 'Friday' ELSE 'Saturday' END AS day_name, "
            "CONCAT(LEFT(cl.start_time, 5), ' - ', LEFT(cl.end_time, 5)) AS time_slot, "
            "CONCAT(f.last_name, ', ', f.first_name) AS faculty, "
            "(SELECT COUNT(*) FROM cor_subjects cs WHERE cs.class_id = cl.id) AS students, cl.status, "
            f"{TERM_LABEL} AS term "
            "FROM classes cl JOIN subjects s ON s.id = cl.subject_id JOIN academic_terms t ON t.id = cl.term_id "
            "LEFT JOIN users f ON f.id = cl.faculty_id "
            f"WHERE {' AND '.join(where)} ORDER BY t.academic_year, t.term_no, s.code, cl.title", params)


def _grades(f):
    where, params = ['1 = 1'], []
    if f['term']:
        where.append('g.academic_year = (SELECT academic_year FROM academic_terms WHERE id = %s) '
                     'AND g.term_no = (SELECT term_no FROM academic_terms WHERE id = %s)')
        params += [f['term'], f['term']]
    return ("SELECT u.username AS student_id, u.last_name, u.first_name, g.academic_year, g.term_no, g.code, "
            "g.title, g.units, g.grade, g.removal_rating "
            "FROM grades g JOIN users u ON u.id = g.user_id "
            f"WHERE {' AND '.join(where)} "
            "ORDER BY g.academic_year, g.term_no, u.last_name, u.first_name, g.code", params)


def _payments(f):
    where, params = ['1 = 1'], []
    if f['date_from']:
        where.append('pm.paid_on >= %s')
        params.append(f['date_from'])
    if f['date_to']:
        where.append('pm.paid_on <= %s')
        params.append(f['date_to'])
    if f['state'] == 'valid':
        where.append('pm.voided_at IS NULL')
    elif f['state'] == 'voided':
        where.append('pm.voided_at IS NOT NULL')
    return ("SELECT pm.receipt_no, pm.paid_on, qt.student_id, u.last_name, u.first_name, qt.account_no, pm.amount, "
            "pm.note, CONCAT(rb.first_name, ' ', rb.last_name) AS recorded_by, "
            "IF(pm.voided_at IS NULL, 'Valid', 'Voided') AS state "
            "FROM payments pm JOIN quotations qt ON qt.id = pm.quotation_id "
            "JOIN applications a ON a.id = qt.application_id JOIN users u ON u.id = a.user_id "
            "LEFT JOIN users rb ON rb.id = pm.recorded_by "
            f"WHERE {' AND '.join(where)} ORDER BY pm.paid_on, pm.id", params)


def _payments_total(rows, f):
    total = sum((r['amount'] for r in rows if r['state'] == 'Valid'), Decimal('0'))
    return rows + [{'receipt_no': 'TOTAL (valid payments only)', 'amount': total}]


def _balances(f):
    where, params = ['qt.archived_at IS NULL'], []
    if f['term']:
        where.append('a.term_id = %s')
        params.append(f['term'])
    return ("SELECT qt.student_id, u.last_name, u.first_name, p.code AS program, "
            f"{TERM_LABEL} AS term, qt.account_no, qt.total, "
            "COALESCE((SELECT SUM(pm.amount) FROM payments pm WHERE pm.quotation_id = qt.id "
            " AND pm.voided_at IS NULL), 0) AS paid "
            "FROM quotations qt JOIN applications a ON a.id = qt.application_id JOIN users u ON u.id = a.user_id "
            "LEFT JOIN programs p ON p.id = a.program_id LEFT JOIN academic_terms t ON t.id = a.term_id "
            f"WHERE {' AND '.join(where)} ORDER BY t.academic_year, t.term_no, u.last_name, u.first_name", params)


def _balances_after(rows, f):
    for r in rows:
        r['balance'] = r['total'] - r['paid']
        r['state'] = 'Fully paid' if r['balance'] <= 0 else 'With balance'
    if f['show'] == 'balance':
        rows = [r for r in rows if r['balance'] > 0]
    return rows + [{'student_id': 'TOTAL', 'total': sum((r['total'] for r in rows), Decimal('0')),
                    'paid': sum((r['paid'] for r in rows), Decimal('0')),
                    'balance': sum((r['balance'] for r in rows), Decimal('0'))}]


def _users(f):
    where, params = ['1 = 1'], []
    if f['role']:
        where.append('u.role = %s')
        params.append(f['role'])
    if f['state'] == 'active':
        where.append('u.is_active = 1')
    elif f['state'] == 'deactivated':
        where.append('u.is_active = 0')
    return ("SELECT u.id, u.username, u.email, u.role, u.last_name, u.first_name, u.middle_name, "
            "IF(u.is_active = 1, 'Active', 'Deactivated') AS state, IF(u.is_activated = 1, 'Yes', 'No') AS activated, "
            "u.last_login, u.created_at FROM users u "
            f"WHERE {' AND '.join(where)} ORDER BY u.role, u.last_name, u.first_name", params)


def _audit(f):
    where, params = ['1 = 1'], []
    if f['date_from']:
        where.append('al.created_at >= %s')
        params.append(f['date_from'])
    if f['date_to']:
        where.append('al.created_at < %s')
        params.append(f['date_to'] + timedelta(days=1))
    return ("SELECT al.created_at, CONCAT(u.first_name, ' ', u.last_name) AS user_name, u.role, al.action, "
            "al.details, al.ip_address FROM audit_logs al LEFT JOIN users u ON u.id = al.user_id "
            f"WHERE {' AND '.join(where)} ORDER BY al.id DESC LIMIT {Report.MAX_ROWS}", params)


DATES = [('date_from', 'From', 'date', None), ('date_to', 'To', 'date', None)]

REPORTS = {
    'registrar': [
        Spec('applications', 'Applications', 'Every submitted application with its status.',
             [('Application No.', 'app_id'), ('Last name', 'last_name'), ('First name', 'first_name'),
              ('Email', 'email'), ('Program', 'program'), ('Applicant type', 'applicant_type'),
              ('Trimester', 'term'), ('Status', 'status'), ('Submitted', 'submitted_at'),
              ('Originals received', 'originals_received_at')],
             _applications, [_term_filter(), ('status', 'Status', 'select',
                                              [('', 'All statuses')] + [(s, s) for s in APPLICATION_STATUSES])]),
        Spec('enrolled', 'Enrolled students', 'Students who are Enrolled, with program, year level and units.',
             [('Student ID', 'student_id'), ('Last name', 'last_name'), ('First name', 'first_name'),
              ('Middle name', 'middle_name'), ('Program', 'program'), ('Year level', 'year_level'),
              ('Student type', 'student_type'), ('Units', 'units'), ('COR status', 'cor_status'),
              ('Date enrolled', 'enrolled_at'), ('Trimester', 'term')],
             _enrolled, [_term_filter()]),
        Spec('classes', 'Class list', 'Every class with its schedule, faculty and number of students.',
             [('Subject code', 'code'), ('Class title', 'title'), ('Units', 'units'), ('Day', 'day_name'),
              ('Time', 'time_slot'), ('Faculty', 'faculty'), ('Students', 'students'), ('Status', 'status'),
              ('Trimester', 'term')],
             _classes, [_term_filter()]),
        Spec('grades', 'Grades', 'The grade of every student in every subject.',
             [('Student ID', 'student_id'), ('Last name', 'last_name'), ('First name', 'first_name'),
              ('Academic year', 'academic_year'), ('Trimester no.', 'term_no'), ('Subject code', 'code'),
              ('Subject title', 'title'), ('Units', 'units'), ('Grade', 'grade'),
              ('Removal rating', 'removal_rating')],
             _grades, [_term_filter()]),
    ],
    'finance': [
        Spec('payments', 'Payments', 'Every payment received, with a total at the end.',
             [('Receipt No.', 'receipt_no'), ('Date paid', 'paid_on'), ('Student ID', 'student_id'),
              ('Last name', 'last_name'), ('First name', 'first_name'), ('Account No.', 'account_no'),
              ('Amount', 'amount'), ('Note', 'note'), ('Recorded by', 'recorded_by'), ('Status', 'state')],
             _payments, DATES + [('state', 'Status', 'select',
                                  [('', 'Valid and voided'), ('valid', 'Valid only'), ('voided', 'Voided only')])],
             after=_payments_total),
        Spec('balances', 'Balances', 'What each student has been billed, has paid and still owes.',
             [('Student ID', 'student_id'), ('Last name', 'last_name'), ('First name', 'first_name'),
              ('Program', 'program'), ('Trimester', 'term'), ('Account No.', 'account_no'),
              ('Total billed', 'total'), ('Paid', 'paid'), ('Balance', 'balance'), ('Status', 'state')],
             _balances, [_term_filter(), ('show', 'Show', 'select',
                                          [('balance', 'Only with a balance'), ('all', 'Everyone')])],
             after=_balances_after),
    ],
    'admin': [
        Spec('users', 'Users', 'Every account, without passwords.',
             [('ID', 'id'), ('Username / Student ID', 'username'), ('Email', 'email'), ('Role', 'role'),
              ('Last name', 'last_name'), ('First name', 'first_name'), ('Middle name', 'middle_name'),
              ('Status', 'state'), ('Activated', 'activated'), ('Last login', 'last_login'),
              ('Created', 'created_at')],
             _users, [('role', 'Role', 'select', list(ROLE_CHOICES)),
                      ('state', 'Status', 'select', [('', 'All'), ('active', 'Active only'),
                                                     ('deactivated', 'Deactivated only')])]),
        Spec('audit', 'Audit logs', f'Who did what and when (up to {50000:,} of the latest entries).',
             [('Date and time', 'created_at'), ('User', 'user_name'), ('Role', 'role'), ('Action', 'action'),
              ('Details', 'details'), ('IP address', 'ip_address')],
             _audit, DATES),
    ],
}


class Report:
    MAX_ROWS = 50000
    MONEY = ('amount', 'total', 'paid', 'balance')

    @staticmethod
    def for_role(role):
        return REPORTS.get(role, [])

    @staticmethod
    def find(role, key):
        return next((s for s in REPORTS.get(role, []) if s.key == key), None)

    @staticmethod
    def term_options():
        rows = query("SELECT id, term_no, academic_year FROM academic_terms "
                     "ORDER BY academic_year DESC, term_no DESC", ())
        return [(r['id'], f"Trimester {r['term_no']}, A.Y. {r['academic_year']}") for r in rows]

    @staticmethod
    def default_term():
        current = Term.current()
        return current.id if current else None

    @classmethod
    def clean(cls, spec, args):
        """Sinusuri ang mga filter mula sa URL. Ibinabalik ang (values, errors)."""
        values = {'term': None, 'status': '', 'state': '', 'show': 'balance', 'role': '',
                  'date_from': None, 'date_to': None}
        errors = []
        term_ids = {t[0] for t in cls.term_options()}
        for name, label, kind, choices in spec.filters:
            raw = args.get(name, '').strip()
            if kind == 'term':
                if raw:
                    if not raw.isdigit() or int(raw) not in term_ids:
                        errors.append('Choose a trimester from the list.')
                    else:
                        values[name] = int(raw)
            elif kind == 'select':
                allowed = {c[0] for c in choices}
                if raw in allowed:
                    values[name] = raw
                elif raw:
                    errors.append(f'{label}: choose from the list.')
                else:
                    values[name] = choices[0][0]
            elif kind == 'date' and raw:
                try:
                    values[name] = datetime.strptime(raw, '%Y-%m-%d').date()
                except ValueError:
                    errors.append(f'{label}: enter a valid date.')
        if values['date_from'] and values['date_to'] and values['date_from'] > values['date_to']:
            errors.append('The "From" date must not be later than the "To" date.')
        return values, errors

    @staticmethod
    def safe(value, money=False):
        """Isang cell ng CSV. Ang text na nagsisimula sa = + - @ ay hindi dapat tumakbo bilang formula sa Excel."""
        if value is None:
            return ''
        if isinstance(value, Decimal):
            return f'{value:.2f}' if money else format(value.normalize(), 'f')
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M')
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        text = str(value)
        if text[:1] in ('=', '+', '-', '@', '\t', '\r'):
            return "'" + text
        return text

    @classmethod
    def csv_text(cls, spec, values):
        """Ibinabalik ang (text ng CSV, bilang ng row). May BOM para tama ang Filipino at 'ñ' sa Excel."""
        sql, params = spec.build(values)
        rows = query(sql, params)
        if spec.after:
            rows = spec.after(rows, values)
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator='\r\n')
        writer.writerow([header for header, _key in spec.columns])
        for row in rows:
            writer.writerow([cls.safe(row.get(key), key in cls.MONEY) for _header, key in spec.columns])
        return '\ufeff' + buf.getvalue(), len(rows)