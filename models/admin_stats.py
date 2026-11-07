from db import query
from models.audit_log import AuditLog
from models.pending_student import PendingStudent
from models.security import Security
from models.stats import Stats
from models.term import Term
from models.trash import Trash


class AdminStats:
    """Mga datos para sa dashboard ng Administrator."""

    ROLES = (('student', 'Students', 'success'), ('applicant', 'Applicants', 'info'), ('faculty', 'Faculty', 'primary'),
             ('registrar', 'Registrar', 'secondary'), ('finance', 'Finance', 'secondary'),
             ('admin', 'Administrators', 'dark'))

    @classmethod
    def dashboard(cls):
        def one(sql, params=()):
            return query(sql, params, one=True)['n']

        counts = {r['role']: r['n'] for r in query("SELECT role, COUNT(*) AS n FROM users WHERE is_active = 1 GROUP BY role")}
        roles = [{'key': k, 'label': label, 'color': color, 'n': counts.get(k, 0)} for k, label, color in cls.ROLES]

        terms = query("SELECT t.term_no, t.academic_year, COUNT(e.id) AS n FROM academic_terms t "
                      "LEFT JOIN enrollments e ON e.term_id = t.id AND e.status = 'Enrolled' "
                      "GROUP BY t.id, t.term_no, t.academic_year ORDER BY t.academic_year DESC, t.term_no DESC LIMIT 6")
        for t in terms:
            t['label'] = f"Trimester {t['term_no']}, {t['academic_year']}"

        current, opened = Term.current(), Term.open_term()
        by_type = Stats.enrolled_by_type(current.id) if current else {}
        events = Security.summary()
        trash = sum(Trash.counts().values())
        return dict(
            pending=len(PendingStudent.all()),
            locked=len(Security.locked_accounts()),
            blocked=len(Security.blocked_ips()),
            failed_logins=events['failed_24h'],
            failed_emails=one("SELECT COUNT(*) AS n FROM email_logs WHERE status = 'Failed' "
                              "AND created_at > NOW() - INTERVAL 1 DAY"),
            skipped_emails=one("SELECT COUNT(*) AS n FROM email_logs WHERE status = 'Skipped' "
                               "AND created_at > NOW() - INTERVAL 1 DAY"),
            trash=trash,
            roles=roles, role_total=sum(r['n'] for r in roles),
            inactive=one("SELECT COUNT(*) AS n FROM users WHERE is_active = 0"),
            not_activated=one("SELECT COUNT(*) AS n FROM users WHERE is_active = 1 AND is_activated = 0"),
            term_rows=terms, term_max=max([t['n'] for t in terms], default=0),
            current_term=current, open_term=opened, enrolled_now=sum(by_type.values()),
            in_process=Term.in_process_count(opened.id) if opened else 0,
            recent=AuditLog.search('', 6, 0)[0],
        )