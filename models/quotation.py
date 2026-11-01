import re
from datetime import date
from decimal import Decimal
from db import query, execute
from models.application import Application
from models.notification import Notification
from models.user import User


class Quotation:
    """Ang tuition quotation ng Finance, kasama ang manual na Student ID. Ang total ay kinukuwenta ng system."""

    # (column, label). Sundan ang Accounting slip ng SIT.
    FEES = (
        ('tuition_fee', 'Tuition Fee'),
        ('energy_fee', 'Energy Fee'),
        ('book_fee', 'Book / Manual'),
        ('printouts_fee', 'Printouts'),
        ('admission_fee', 'Admission'),
    )
    STUDENT_ID_RE = re.compile(r'^\d{2}-[1-3]-\d{4}$')          # YY-T-NNNN, hal. 26-2-0110
    ACCOUNT_RE = re.compile(r'^[A-Za-z0-9-]{3,20}$')
    MONEY_RE = re.compile(r'^\d{1,7}(\.\d{1,2})?$')
    UNITS_RE = re.compile(r'^\d{1,2}(\.\d)?$')

    @staticmethod
    def find(application_id):
        return query("SELECT * FROM quotations WHERE application_id = %s", (application_id,), one=True)

    @staticmethod
    def application_for_finance(application_id):
        """Ang application kung puwede pang i-quote: For Enrollment, may Originals received, hindi archived ang term."""
        application = Application.find(application_id)
        if application is None or application.status != 'For Enrollment' or not application.originals_received_at:
            return None
        if application.term_id:
            term = query("SELECT admission_status FROM academic_terms WHERE id = %s", (application.term_id,), one=True)
            if term and term['admission_status'] == 'Archived':
                return None
        return application

    @staticmethod
    def suggest_account_no():
        n = query("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM quotations", (), one=True)['n']
        return f'AC-{date.today().year}-{n:04d}'

    @staticmethod
    def to_form(row):
        """Ang naka-save na quotation bilang text, para sa form."""
        form = {'student_id': row['student_id'], 'account_no': row['account_no'],
                'units': format(row['units'].normalize(), 'f')}
        for name, _label in Quotation.FEES:
            form[name] = '{:.2f}'.format(row[name])
        return form

    @classmethod
    def clean(cls, form, application_id):
        """Sinusuri ang form. Ibinabalik ang (data, errors). Ang total ay kinukuwenta dito, hindi galing sa form."""
        data, errors = {}, []

        student_id = form.get('student_id', '').strip()
        if not cls.STUDENT_ID_RE.match(student_id):
            errors.append('Student ID must look like 26-2-0110 (year, trimester 1 to 3, number).')
        elif query("SELECT id FROM users WHERE username = %s", (student_id,), one=True) or \
                query("SELECT id FROM quotations WHERE student_id = %s AND application_id <> %s",
                      (student_id, application_id), one=True):
            errors.append(f'Student ID {student_id} is already taken.')
        data['student_id'] = student_id

        account_no = form.get('account_no', '').strip().upper()
        if not cls.ACCOUNT_RE.match(account_no):
            errors.append('Account No. may only contain letters, numbers and hyphens (3 to 20 characters).')
        elif query("SELECT id FROM quotations WHERE account_no = %s AND application_id <> %s",
                   (account_no, application_id), one=True):
            errors.append(f'Account No. {account_no} is already used.')
        data['account_no'] = account_no

        raw = form.get('units', '').strip()
        if cls.UNITS_RE.match(raw) and Decimal(raw) > 0:
            data['units'] = Decimal(raw)
        else:
            errors.append('Enter the number of units (greater than 0).')
            data['units'] = Decimal('0')

        total = Decimal('0')
        for name, label in cls.FEES:
            raw = form.get(name, '').strip().replace(',', '')
            if raw == '':
                value = Decimal('0')
            elif cls.MONEY_RE.match(raw):
                value = Decimal(raw)
            else:
                errors.append(f'{label} must be an amount like 1500 or 1500.50.')
                value = Decimal('0')
            data[name] = value
            total += value
        if data['tuition_fee'] <= 0 and not any(label.startswith('Tuition') for label in
                                                 [e for e in errors if e.startswith('Tuition')]):
            errors.append('Enter the Tuition Fee.')
        data['total'] = total
        return data, errors

    @classmethod
    def save(cls, application, data, by_user):
        """Ini-insert o ina-update ang quotation. Ibinabalik ang True kung bago."""
        if not application.term_id:
            raise ValueError('This application has no term yet.')
        existing = cls.find(application.id)
        fee_cols = [name for name, _label in cls.FEES]
        values = [data['student_id'], data['account_no'], data['units']] + [data[c] for c in fee_cols] + [data['total']]

        if existing:
            sets = ', '.join(f'{c} = %s' for c in ['student_id', 'account_no', 'units'] + fee_cols + ['total'])
            execute(f"UPDATE quotations SET {sets} WHERE application_id = %s", values + [application.id])
        else:
            cols = ', '.join(['application_id', 'student_id', 'account_no', 'units'] + fee_cols +
                             ['total', 'created_by'])
            marks = ', '.join(['%s'] * (len(fee_cols) + 6))
            execute(f"INSERT INTO quotations ({cols}) VALUES ({marks})",
                    [application.id] + values + [by_user.id])

        # Ang enrollment record: Quoted na. (Hindi ibababa kung Enrolled na.)
        execute("INSERT INTO enrollments (user_id, term_id, student_type, status) VALUES (%s, %s, %s, 'Quoted') "
                "ON DUPLICATE KEY UPDATE student_type = VALUES(student_type), "
                "status = IF(status = 'Enrolled', status, 'Quoted')",
                (application.user_id, application.term_id, application.applicant_type))

        owner = User.find(application.user_id)
        details = [('Student ID', data['student_id']), ('Account No.', data['account_no']),
                   ('Total', 'PHP {:,.2f}'.format(data['total']))]
        if existing:
            Notification.notify(owner, 'Your SIT quotation was updated', 'Quotation updated',
                                'The Finance office updated your tuition quotation. Please see the new total below.',
                                details)
        else:
            Notification.notify(owner, 'Your SIT tuition quotation', 'Tuition quotation ready',
                                'Your tuition quotation is ready. Please see the Finance office. '
                                'After this, the Registrar will give your Certificate of Enrolment.',
                                details)
        return existing is None