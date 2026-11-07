from db import query
from models.announcement import Announcement
from models.class_offering import ClassOffering
from models.teaching import Teaching


class FacultyStats:
    """Mga datos para sa dashboard ng Faculty: ang mga klase niya ngayong term at ang mga grade na kulang pa."""

    @staticmethod
    def dashboard(user):
        terms = ClassOffering.terms()
        term = ClassOffering.pick_term(terms, None)
        classes = Teaching.classes(user.id, term['id']) if term else []
        for c in classes:
            c['graded'] = query(
                "SELECT COUNT(*) AS n FROM cor_subjects cs JOIN cors r ON r.id = cs.cor_id "
                "JOIN grades g ON g.user_id = r.user_id AND g.academic_year = %s AND g.term_no = %s AND g.code = %s "
                "WHERE cs.class_id = %s", (term['academic_year'], term['term_no'], c['code'], c['id']), one=True)['n']
        students = sum(c['student_count'] for c in classes)
        graded = sum(min(c['graded'], c['student_count']) for c in classes)
        return dict(term=term, classes=classes, students=students, to_grade=students - graded,
                    announcements=Announcement.for_role('faculty', 3))