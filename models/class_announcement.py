from db import query, execute


class ClassAnnouncement:
    """Announcements scoped to a single class. Student reads are restricted by their COR."""

    @staticmethod
    def for_class(class_id):
        return query("SELECT * FROM class_announcements WHERE class_id = %s AND deleted_at IS NULL "
                     "ORDER BY created_at DESC, id DESC", (class_id,))

    @staticmethod
    def create(class_id, title, body, user_id):
        title = ' '.join((title or '').split())
        body = (body or '').strip()
        errors = []
        if not 3 <= len(title) <= 120:
            errors.append('Announcement title must be 3 to 120 characters.')
        if not 10 <= len(body) <= 3000:
            errors.append('Announcement must be 10 to 3,000 characters.')
        if errors:
            return None, errors
        ident = execute("INSERT INTO class_announcements (class_id, title, body, created_by) "
                        "VALUES (%s, %s, %s, %s)", (class_id, title, body, user_id))
        execute("INSERT INTO notifications (user_id, title, message) "
                "SELECT DISTINCT co.user_id, 'New class announcement', %s FROM cor_subjects cs "
                "JOIN cors co ON co.id = cs.cor_id WHERE cs.class_id = %s",
                (f'{title}: {body[:400]}'[:500], class_id))
        return ident, []

    @staticmethod
    def delete(class_id, announcement_id):
        execute("UPDATE class_announcements SET deleted_at = NOW() "
                "WHERE id = %s AND class_id = %s AND deleted_at IS NULL", (announcement_id, class_id))

    @staticmethod
    def for_student(user_id):
        rows = query(
            "SELECT ca.*, c.title AS class_title, s.code, c.term_id, t.term_no, t.academic_year FROM class_announcements ca "
            "JOIN classes c ON c.id = ca.class_id JOIN subjects s ON s.id = c.subject_id "
            "JOIN academic_terms t ON t.id = c.term_id "
            "WHERE ca.deleted_at IS NULL AND t.is_current = 1 AND EXISTS ("
            "SELECT 1 FROM cor_subjects cs JOIN cors co ON co.id = cs.cor_id "
            "WHERE cs.class_id = ca.class_id AND co.user_id = %s) "
            "ORDER BY ca.created_at DESC, ca.id DESC", (user_id,))
        grouped = {}
        for row in rows:
            grouped.setdefault(row['class_id'], []).append(row)
        return grouped
    @staticmethod
    def classes_for_student(user_id):
        return query(
            "SELECT DISTINCT c.id AS class_id, c.title AS class_title, s.code, t.term_no, t.academic_year "
            "FROM cor_subjects cs JOIN cors co ON co.id = cs.cor_id "
            "JOIN classes c ON c.id = cs.class_id JOIN subjects s ON s.id = c.subject_id "
            "JOIN academic_terms t ON t.id = c.term_id "
            "WHERE co.user_id = %s AND t.is_current = 1 ORDER BY s.code", (user_id,))

