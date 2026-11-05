import re
from datetime import date, datetime
from db import query, execute
from models.user import User
from models.notification import Notification
from models.application_document import ApplicationDocument

TEXT_RE = re.compile(r"^[\w\s.,'\u2019\-&()/#]+$", re.UNICODE)
PHONE_RE = re.compile(r'^(09\d{9}|\+639\d{9})$')
HOME_TEL_RE = re.compile(r'^[\d\s()+\-]{5,20}$')


class Application:
    """Isang application ng isang applicant (isa lang bawat user)."""

    # --- mga field na puwedeng i-edit ng applicant ---
    FIELDS = (
        'applicant_type', 'program_id', 'address', 'home_tel', 'phone',
        'father_name', 'father_mobile', 'mother_name', 'mother_mobile',
        'birthdate', 'birthplace', 'gender', 'civil_status', 'nationality',
        'school_name', 'school_place', 'year_graduated',
        'job_position', 'employer',
        'church_name', 'church_address', 'pastor_name',
        'responsibility', 'ministry',
    )

    # Kailangang kumpleto bago mag-submit. Optional: Home Tel., Employment, Ministry.
    # Dagdag na patakaran: kailangan ng kahit isa sa father o mother (pangalan at contact).
    REQUIRED = {
        'program_id': 'Degree program', 'address': 'Complete address', 'phone': 'Phone number',
        'birthdate': 'Date of birth', 'birthplace': 'Place of birth', 'gender': 'Gender',
        'civil_status': 'Civil status', 'nationality': 'Nationality',
        'school_name': 'Name of school', 'school_place': 'Place of school', 'year_graduated': 'Year graduated',
        'church_name': 'Name of church', 'church_address': 'Church address', 'pastor_name': 'Pastor',
    }
    PARENT_LABEL = 'Father or mother (name and contact number)'

    TEXT_FIELDS = {
        'address': ('Complete address', 255), 'birthplace': ('Place of birth', 120),
        'nationality': ('Nationality', 60), 'father_name': ('Name of father', 120),
        'mother_name': ('Name of mother', 120), 'school_name': ('Name of school', 150),
        'school_place': ('Place of school', 150), 'job_position': ('Position', 100),
        'employer': ('Employer', 150), 'church_name': ('Name of church', 150),
        'church_address': ('Church address', 255), 'pastor_name': ('Pastor', 120),
        'responsibility': ('Responsibility', 150), 'ministry': ('Ministry', 150),
    }
    PHONE_FIELDS = {'phone': 'Phone number', 'father_mobile': "Father's contact number",
                    'mother_mobile': "Mother's contact number"}
    CHOICES = {
        'applicant_type': ('New', 'Transferee'),
        'gender': ('Male', 'Female'),
        'civil_status': ('Single', 'Married', 'Widowed', 'Separated'),
    }

    # --- status at tracker ---
    STATUSES = ('Draft', 'Submitted', 'Approved', 'Interview Scheduled', 'For Enrollment',
                'Enrolled', 'Rejected')
    STATUS_STEPS = ('Application', 'Review', 'Interview', 'Enrollment', 'Enrolled')
    STEP_OF = {'Draft': 0, 'Submitted': 1, 'Approved': 2, 'Interview Scheduled': 2,
               'For Enrollment': 3, 'Enrolled': 4}
    INTERVIEWERS = ('Executive Director', 'Dean')

    def __init__(self, row=None):
        for name in ('id', 'user_id', 'term_id', 'remarks', 'submitted_at', 'originals_received_at',
                     'certified_name', 'certified_at') + self.FIELDS:
            setattr(self, name, None)
        self.status = 'Draft'
        self.applicant_type = 'New'
        for key, value in (row or {}).items():
            setattr(self, key, value)

    # ---------- mga kailangang dokumento ----------
    def required_documents(self):
        """Mga dokumentong hinihingi para sa program at uri ng applicant (New o Transferee)."""
        if not self.program_id:
            return []
        rows = query("SELECT dt.* FROM document_types dt "
                     "JOIN program_documents pd ON pd.document_type_id = dt.id "
                     "WHERE pd.program_id = %s AND pd.applicant_type = %s ORDER BY dt.id",
                     (self.program_id, self.applicant_type or 'New'))
        docs = []
        for r in rows:
            name = r.get('name') or r.get('title') or r.get('document_name') or f'Document {r["id"]}'
            docs.append({'id': r['id'], 'name': name, 'online': False})   # lahat ay ina-upload na
        return docs

    def photo_type_id(self):
        """Ang document_type_id ng na-upload na 2x2 na larawan (JPG o PNG lang), kung mayroon."""
        for row in self.document_rows():
            upload = row['upload']
            if '2x2' in row['name'].lower() and upload and upload['mime_type'] in ('image/jpeg', 'image/png'):
                return row['id']
        return None

    def document_rows(self):
        """Bawat kailangang dokumento, kasama ang na-upload at kung puwede pang baguhin."""
        uploads = ApplicationDocument.for_application(self.id)
        rows = []
        for doc in self.required_documents():
            upload = uploads.get(doc['id'])
            if doc['online']:
                can_change = False
            elif self.status == 'Draft':
                can_change = True
            elif self.status == 'Submitted':
                can_change = bool(upload and upload['status'] == 'Rejected')   # tinanggihan lang ang mapapalitan
            else:
                can_change = False
            rows.append({**doc, 'upload': upload, 'can_change': can_change,
                         'can_delete': self.status == 'Draft' and bool(upload)})
        return rows

    def readiness(self):
        """Mga kulang bago makapag-submit. Walang laman = handa na."""
        problems = []
        missing = self.missing()
        if missing:
            problems.append(f'Complete the application form ({len(missing)} required details missing).')
        lacking = [r['name'] for r in self.document_rows() if not r['online'] and not r['upload']]
        if lacking:
            problems.append('Upload: ' + ', '.join(lacking) + '.')
        return problems

    # ---------- pagbabago ng status ----------
    def _set_status(self, status):
        execute("UPDATE applications SET status = %s WHERE id = %s", (status, self.id))
        self.status = status

    def _owner(self):
        return User.find(self.user_id)

    def submit(self, signature=''):
        if self.status != 'Draft':
            raise ValueError('This application was already submitted.')
        problems = self.readiness()
        if problems:
            raise ValueError(' '.join(problems))
        owner = self._owner()
        signature = ' '.join((signature or '').split())
        # Ang pirma ay ang buong pangalan na tina-type niya; dapat nandoon ang given name at surname ng account
        if not all(part.lower() in signature.lower() for part in (owner.first_name, owner.last_name)):
            raise ValueError("Sign by typing your full name (given name and surname) as it appears in your account.")
        execute("UPDATE applications SET status = 'Submitted', submitted_at = NOW(), "
                "certified_name = %s, certified_at = NOW() WHERE id = %s", (signature[:120], self.id))
        self.status = 'Submitted'
        Notification.notify(self._owner(), 'We received your SIT application', 'Application received',
                            'Thank you! Your application and documents are now with the Registrar for review. '
                            'We will notify you here and by email once there is an update.')

    def current_interview(self):
        return query("SELECT * FROM interviews WHERE application_id = %s AND status = 'Scheduled' "
                     "ORDER BY id DESC LIMIT 1", (self.id,), one=True)

    # ---------- Approval ----------
    def approval_blockers(self):
        """Mga dahilan kung bakit hindi pa puwedeng i-approve."""
        rows = [r for r in self.document_rows() if not r['online']]
        problems = []
        lacking = [r['name'] for r in rows if not r['upload']]
        unverified = [r['name'] for r in rows if r['upload'] and r['upload']['status'] != 'Verified']
        if lacking:
            problems.append('Not yet uploaded: ' + ', '.join(lacking) + '.')
        if unverified:
            problems.append('Verify first: ' + ', '.join(unverified) + '.')
        return problems

    def approve(self, by_user, interview=None):
        """Aprubahan ang application. Kung may `interview`, sabay na ang schedule at isang email lang."""
        if self.status != 'Submitted':
            raise ValueError('Only submitted applications can be approved.')
        blockers = self.approval_blockers()
        if blockers:
            raise ValueError(' '.join(blockers))
        if interview:
            booked = self._book(by_user, **interview)
            self._notify_interview(booked, approved=True)
        else:
            self._set_status('Approved')
            Notification.notify(self._owner(), 'Your SIT application was approved', 'Application approved',
                                'Congratulations! Your application has been approved. '
                                'Your interview schedule will be sent to you soon.')

    def reject(self, by_user, reason):
        if self.status not in ('Submitted', 'Approved', 'Interview Scheduled', 'For Enrollment'):
            raise ValueError('This application can no longer be rejected.')
        reason = ' '.join((reason or '').split())
        if not 3 <= len(reason) <= 500:
            raise ValueError('Give a short reason (3 to 500 characters).')
        execute("UPDATE applications SET status = 'Rejected', remarks = %s WHERE id = %s", (reason, self.id))
        execute("UPDATE interviews SET status = 'Cancelled' WHERE application_id = %s AND status = 'Scheduled'",
                (self.id,))
        self.status = 'Rejected'
        Notification.notify(self._owner(), 'Update on your SIT application', 'Application not approved',
                            f'We are sorry, your application was not approved. Reason: {reason}',
                            [('Reason', reason)])

    def pass_interview(self, by_user):
        if self.status != 'Interview Scheduled':
            raise ValueError('Only applicants with a scheduled interview can be marked as passed.')
        execute("UPDATE interviews SET status = 'Done' WHERE application_id = %s AND status = 'Scheduled'",
                (self.id,))
        self._set_status('For Enrollment')
        Notification.notify(self._owner(), 'Your SIT interview is complete', 'Interview complete',
                            'Your interview is complete and you are now cleared for enrollment. '
                            'The school will contact you about the next steps.')

    def receive_originals(self, by_user):
        """Natanggap na ng Registrar ang orihinal na dokumento. Pagkatapos nito, puwede nang i-quote ng Finance."""
        if self.status != 'For Enrollment':
            raise ValueError('Original documents are received after the interview is passed.')
        if self.originals_received_at:
            raise ValueError('The original documents were already received.')
        execute("UPDATE applications SET originals_received_at = NOW() WHERE id = %s", (self.id,))
        self.originals_received_at = datetime.now()
        Notification.notify(self._owner(), 'Original documents received', 'Original documents received',
                            'The Registrar has received your original documents. '
                            'Please proceed to the Finance office for your tuition quotation.')

    def schedule_interview(self, by_user, **interview):
        if self.status not in ('Approved', 'Interview Scheduled'):
            raise ValueError('Approve the application first.')
        booked = self._book(by_user, **interview)
        self._notify_interview(booked, approved=False)

    def _book(self, by_user, interviewer, scheduled_at, venue, notes=None):
        if interviewer not in self.INTERVIEWERS:
            raise ValueError('Choose the Executive Director or the Dean.')
        if scheduled_at <= datetime.now():
            raise ValueError('The interview must be in the future.')
        venue = ' '.join((venue or '').split())
        if not venue:
            raise ValueError('Enter the venue.')
        execute("UPDATE interviews SET status = 'Rescheduled' WHERE application_id = %s AND status = 'Scheduled'",
                (self.id,))
        execute("INSERT INTO interviews (application_id, interviewer, scheduled_at, venue, notes, created_by) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (self.id, interviewer, scheduled_at, venue, notes, by_user.id if by_user else None))
        self._set_status('Interview Scheduled')
        return {'interviewer': interviewer, 'scheduled_at': scheduled_at, 'venue': venue, 'notes': notes}

    def _notify_interview(self, interview, approved):
        when = interview['scheduled_at']
        details = [('Interview with', interview['interviewer']),
                   ('Date', when.strftime('%A, %B %d, %Y')),
                   ('Time', when.strftime('%I:%M %p').lstrip('0')),
                   ('Venue', interview['venue'])]
        if interview.get('notes'):
            details.append(('Note', interview['notes']))
        checklist = [f'{d["name"]} (original and photocopy)' for d in self.required_documents() if not d['online']]
        lead = 'Congratulations! Your application has been approved. ' if approved else ''
        message = (f'{lead}Your interview with the {interview["interviewer"]} is scheduled. '
                   'Please bring your documents on the day of the interview.')
        Notification.notify(self._owner(), 'Your SIT interview schedule', 'Interview schedule',
                            message, details, checklist)

    # ---------- paghahanap ----------
    @classmethod
    def find_by_user(cls, user_id):
        row = query("SELECT * FROM applications WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,), one=True)
        return cls(row) if row else None

    @classmethod
    def find(cls, application_id):
        row = query("SELECT * FROM applications WHERE id = %s", (application_id,), one=True)
        return cls(row) if row else None

    @classmethod
    def search(cls, q='', status='', limit=10, offset=0, term_id=None):
        """Para sa Registrar: mga na-submit na application (walang Draft). Ibinabalik ang (rows, total)."""
        where, params = ["a.status <> 'Draft'", "a.applicant_type IN ('New', 'Transferee')"], []
        if term_id:
            where.append('a.term_id = %s')
            params.append(term_id)
        if status:
            where.append('a.status = %s')
            params.append(status)
        if q:
            like = f'%{q}%'
            where.append('(u.first_name LIKE %s OR u.last_name LIKE %s OR u.email LIKE %s)')
            params += [like, like, like]
        base = 'FROM applications a JOIN users u ON u.id = a.user_id WHERE ' + ' AND '.join(where)
        total = query(f'SELECT COUNT(*) AS n {base}', params, one=True)['n']
        rows = query(
            'SELECT a.id, a.status, a.applicant_type, a.program_id, a.submitted_at, u.first_name, u.last_name, u.email, '
            '(SELECT COUNT(*) FROM application_documents d WHERE d.application_id = a.id) AS docs_uploaded, '
            "(SELECT COUNT(*) FROM application_documents d WHERE d.application_id = a.id AND d.status = 'Verified') AS docs_verified, "
            "(SELECT COUNT(*) FROM application_documents d WHERE d.application_id = a.id AND d.status = 'Rejected') AS docs_rejected "
            f"{base} ORDER BY (a.status = 'Submitted') DESC, a.submitted_at DESC, a.id DESC LIMIT %s OFFSET %s",
            params + [limit, offset])
        return rows, total

    @staticmethod
    def program_options():
        """Listahan ng (id, pangalan) ng mga program para sa dropdown."""
        options = []
        for r in query("SELECT * FROM programs ORDER BY id"):
            if not r.get('is_active', 1):
                continue
            name = r.get('name') or r.get('title') or r.get('program_name') or ''
            code = r.get('code') or r.get('short_name') or ''
            label = f'{name} ({code})' if name and code else (name or code or f'Program {r["id"]}')
            options.append((r['id'], label))
        return options

    # ---------- state ----------
    @property
    def is_editable(self):
        return self.status == 'Draft'

    @property
    def is_closed(self):
        return self.status == 'Rejected'

    @property
    def step_index(self):
        return self.STEP_OF.get(self.status, 0)

    def missing(self):
        """Mga kailangang detalye na wala pang laman."""
        gaps = [label for name, label in self.REQUIRED.items() if getattr(self, name) in (None, '')]
        has_parent = (self.father_name and self.father_mobile) or (self.mother_name and self.mother_mobile)
        if not has_parent:
            gaps.append(self.PARENT_LABEL)
        return gaps

    @property
    def progress(self):
        total = len(self.REQUIRED) + 1                      # +1 para sa father/mother
        return total - len(self.missing()), total

    @property
    def age(self):
        """Kinukuwenta mula sa birthdate, kaya hindi na kailangang i-save."""
        born = self.birthdate
        if not born:
            return None
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def to_form(self):
        """Ang mga value bilang text, para sa form."""
        form = {}
        for name in self.FIELDS:
            value = getattr(self, name)
            form[name] = '' if value is None else (value.isoformat() if isinstance(value, date) else str(value))
        return form

    # ---------- pag-save ----------
    def save(self):
        values = [getattr(self, name) for name in self.FIELDS]
        if self.id is None:
            columns = ', '.join(('user_id', 'term_id') + self.FIELDS)
            marks = ', '.join(['%s'] * (len(self.FIELDS) + 2))
            self.id = execute(f"INSERT INTO applications ({columns}) VALUES ({marks})",
                              [self.user_id, self.term_id] + values)
        else:
            sets = ', '.join(f'{name} = %s' for name in self.FIELDS)
            execute(f"UPDATE applications SET {sets} WHERE id = %s", values + [self.id])

    # ---------- validation ----------
    @classmethod
    def clean(cls, form, valid_programs):
        """Sinusuri ang laman ng form. Ibinabalik ang (data, errors). Puwedeng hindi pa kumpleto (draft)."""
        data, errors = {}, []
        today = date.today()

        raw = form.get('program_id', '').strip()
        if raw and (not raw.isdigit() or int(raw) not in valid_programs):
            errors.append('Choose a valid degree program.')
            raw = ''
        data['program_id'] = int(raw) if raw else None

        raw = form.get('birthdate', '').strip()
        data['birthdate'] = None
        if raw:
            try:
                born = date.fromisoformat(raw)
                if not 10 <= (today - born).days / 365.25 <= 100:
                    raise ValueError
                data['birthdate'] = born
            except ValueError:
                errors.append('Enter a valid date of birth.')

        for name, (label, limit) in cls.TEXT_FIELDS.items():
            value = ' '.join(form.get(name, '').split())
            if len(value) > limit or (value and not TEXT_RE.match(value)):
                errors.append(f'{label} has invalid characters or is too long.')
            data[name] = value or None

        for name, label in cls.PHONE_FIELDS.items():
            digits = re.sub(r'[\s-]', '', form.get(name, ''))
            if digits and not PHONE_RE.match(digits):
                errors.append(f'{label} must look like 09171234567.')
            data[name] = digits or None

        home = ' '.join(form.get('home_tel', '').split())
        if home and not HOME_TEL_RE.match(home):
            errors.append('Home telephone may only contain digits, spaces, + ( ) and -.')
        data['home_tel'] = home or None

        for name, options in cls.CHOICES.items():
            value = form.get(name, '')
            if value and value not in options:
                errors.append('Please choose a valid option.')
                value = ''
            data[name] = value or None

        data['applicant_type'] = data.get('applicant_type') or 'New'

        raw = form.get('year_graduated', '').strip()
        data['year_graduated'] = None
        if raw:
            if raw.isdigit() and 1950 <= int(raw) <= today.year:
                data['year_graduated'] = int(raw)
            else:
                errors.append(f'Year graduated must be between 1950 and {today.year}.')

        return data, errors