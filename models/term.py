import re
from datetime import date
from db import query, execute

YEAR_RE = re.compile(r'^(\d{4})-(\d{4})$')


class Term:
    """Isang trimester ng isang academic year, kasama ang admission window nito."""

    NAMES = {1: 'First', 2: 'Second', 3: 'Third'}

    def __init__(self, row):
        self.__dict__.update(row)

    # ---------- itsura ----------
    @property
    def name(self):
        return f'{self.NAMES.get(self.term_no, self.term_no)} Trimester, A.Y. {self.academic_year}'

    @property
    def short(self):
        return f'Trimester {self.term_no}, A.Y. {self.academic_year}'

    @property
    def is_open(self):
        return self.admission_status == 'Open'

    # ---------- paghahanap ----------
    @staticmethod
    def sync():
        """Ang bukas na window na lampas na sa closing date ay isinasara."""
        execute("UPDATE academic_terms SET admission_status = 'Closed' "
                "WHERE admission_status = 'Open' AND admission_close IS NOT NULL AND admission_close < CURDATE()")

    @classmethod
    def all(cls):
        cls.sync()
        return [cls(r) for r in query("SELECT * FROM academic_terms ORDER BY academic_year DESC, term_no DESC")]

    @classmethod
    def find(cls, term_id):
        cls.sync()
        row = query("SELECT * FROM academic_terms WHERE id = %s", (term_id,), one=True)
        return cls(row) if row else None

    @classmethod
    def open_term(cls):
        """Ang kasalukuyang bukas na admission window (isa lang), o None."""
        cls.sync()
        row = query("SELECT * FROM academic_terms WHERE admission_status = 'Open' ORDER BY id DESC LIMIT 1", one=True)
        return cls(row) if row else None

    @classmethod
    def active(cls):
        """Mga term na may aktibong admission (Open o Closed pa lang, hindi pa naka-archive). Una ang bukas."""
        cls.sync()
        rows = query("SELECT * FROM academic_terms WHERE admission_status IN ('Open', 'Closed') "
                     "ORDER BY (admission_status = 'Open') DESC, academic_year DESC, term_no DESC")
        return [cls(r) for r in rows]

    # ---------- validation ----------
    @staticmethod
    def _to_date(raw, label):
        raw = (raw or '').strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            raise ValueError(f'{label} is not a valid date.')

    @classmethod
    def _dates(cls, opens, closes):
        opens, closes = cls._to_date(opens, 'Opening date'), cls._to_date(closes, 'Closing date')
        if opens and closes and closes < opens:
            raise ValueError('The closing date must be on or after the opening date.')
        return opens, closes

    # ---------- pagbabago ----------
    @classmethod
    def create(cls, term_no, academic_year, opens, closes):
        term_no = int(term_no) if str(term_no).isdigit() else 0
        if term_no not in cls.NAMES:
            raise ValueError('Choose trimester 1, 2 or 3.')
        academic_year = (academic_year or '').strip()
        match = YEAR_RE.match(academic_year)
        if not match or int(match.group(2)) != int(match.group(1)) + 1:
            raise ValueError('Academic year must look like 2026-2027.')
        if query("SELECT id FROM academic_terms WHERE term_no = %s AND academic_year = %s",
                 (term_no, academic_year), one=True):
            raise ValueError('That trimester already exists for this academic year.')
        opens, closes = cls._dates(opens, closes)
        return execute("INSERT INTO academic_terms (term_no, academic_year, admission_open, admission_close) "
                       "VALUES (%s, %s, %s, %s)", (term_no, academic_year, opens, closes))

    @classmethod
    def update_dates(cls, term_id, opens, closes):
        term = cls.find(term_id)
        if term is None:
            raise ValueError('Term not found.')
        if term.admission_status == 'Archived':
            raise ValueError('An archived term can no longer be edited.')
        opens, closes = cls._dates(opens, closes)
        execute("UPDATE academic_terms SET admission_open = %s, admission_close = %s WHERE id = %s",
                (opens, closes, term_id))

    @classmethod
    def open_window(cls, term_id):
        term = cls.find(term_id)
        if term is None:
            raise ValueError('Term not found.')
        if term.admission_status not in ('Draft', 'Closed'):
            raise ValueError('This admission window cannot be opened.')
        if term.admission_close is None:
            raise ValueError('Set the closing date first.')
        if term.admission_close < date.today():
            raise ValueError('The closing date has already passed. Set a later date first.')
        current = cls.open_term()
        if current and current.id != term.id:
            raise ValueError(f'{current.short} is still open. Close it first.')
        execute("UPDATE academic_terms SET admission_status = 'Open' WHERE id = %s", (term_id,))

    @classmethod
    def close_window(cls, term_id):
        term = cls.find(term_id)
        if term is None or term.admission_status != 'Open':
            raise ValueError('Only an open admission window can be closed.')
        execute("UPDATE academic_terms SET admission_status = 'Closed' WHERE id = %s", (term_id,))