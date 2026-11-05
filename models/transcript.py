from datetime import date
from db import query
from models.grade import Grade
from models.registrar_record import RegistrarRecord


def long_date(d):
    return f'{d:%B} {d.day}, {d:%Y}'


class Transcript:
    """Ang Official Transcript of Record at ang Grade Report, ayon sa format ng SIT."""

    ROWS_PER_PAGE = 16
    SIGNATORIES = (('Prepared by:', 'MS. LARA KRYSTEL F. BONIFACIO'),
                   ('Checked and Verified by:', 'REV. JOHN LOUIE B. REYES'),
                   ('Approved by:', 'DR. VIRGILIO G. BENOSA, JR.'))

    @staticmethod
    def tor(user_id):
        rec = RegistrarRecord.find(user_id)
        if rec is None:
            return None
        info = RegistrarRecord.tor_info(user_id)
        first = query("SELECT t.term_no, t.academic_year FROM cors c JOIN academic_terms t ON t.id = c.term_id "
                      "WHERE c.user_id = %s ORDER BY t.academic_year, t.term_no LIMIT 1", (user_id,), one=True)
        head = {
            'name': rec['name'], 'address': rec['address'] or '',
            'birthdate': long_date(rec['birthdate']) if rec['birthdate'] else '',
            'birthplace': rec['birthplace'] or '',
            'last_attended': info['last_attended'], 'category': info['category'], 'school': info['school'],
            'degree': info['degree'] or rec['program_name'] or '', 'major': info['major'],
            'admitted': info['admitted'] or (Grade.term_label(first['term_no'], first['academic_year']) if first else ''),
            'conferred': info['conferred'],
        }
        rows = []
        for g in Grade.grouped(Grade.for_student(user_id)):
            for i, r in enumerate(g['rows']):
                rows.append({'term': g['label'] if i == 0 else '', 'group': g['label'], 'code': r['code'],
                             'title': r['title'], 'grade': r['grade'], 'removal': r['removal_rating'] or '',
                             'units': r['units']})
        size = Transcript.ROWS_PER_PAGE
        pages = [rows[i:i + size] for i in range(0, len(rows), size)] or [[]]
        for page in pages:                      # kapag naputol ang term sa pahina, ulitin ang pangalan ng term
            if page and not page[0]['term']:
                page[0]['term'] = page[0]['group']
        return {'head': head, 'pages': pages, 'date_issued': long_date(date.today()),
                'signatories': Transcript.SIGNATORIES, 'scale': Grade.SCALE, 'other': Grade.OTHER}

    @staticmethod
    def grade_report(user_id, academic_year, term_no):
        rec = RegistrarRecord.find(user_id)
        if rec is None or term_no not in Grade.TERM_NAMES:
            return None
        rows = [r for r in Grade.for_student(user_id)
                if r['academic_year'] == academic_year and r['term_no'] == term_no]
        year = query("SELECT c.year_level FROM cors c JOIN academic_terms t ON t.id = c.term_id "
                     "WHERE c.user_id = %s AND t.academic_year = %s AND t.term_no = %s",
                     (user_id, academic_year, term_no), one=True)
        return {'rec': rec, 'rows': rows, 'year': year['year_level'] if year else '',
                'heading': f"{Grade.SHORT[term_no]} Trim. AY: {Grade.short_ay(academic_year)}",
                'date': long_date(date.today()), 'scale': Grade.SCALE, 'other': Grade.OTHER}