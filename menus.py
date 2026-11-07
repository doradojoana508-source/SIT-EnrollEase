ROLE_LABELS = {
    'applicant': 'Applicant', 'student': 'Student', 'admin': 'Administrator',
    'registrar': 'Registrar', 'finance': 'Finance', 'faculty': 'Faculty',
}

# (label, bootstrap icon, endpoint). Dadagdagan natin ito sa bawat susunod na hakbang.
MENUS = {
    'applicant': [
        ('Dashboard', 'bi-speedometer2', 'applicant.dashboard'),
        ('My Application', 'bi-journal-text', 'applicant.application'),
        ('Documents', 'bi-folder2-open', 'applicant.documents'),
        ('Announcements', 'bi-megaphone', 'applicant_news.index'),],
    'student': [
        ('Dashboard', 'bi-speedometer2', 'portal.dashboard'),
        ('COR & Schedule', 'bi-card-checklist', 'portal_student.cor'),
        ('Pre-Enrollment', 'bi-pencil-square', 'portal_enroll.index'),
        ('Grades', 'bi-award', 'portal_grades.index'),
        ('Library', 'bi-book', 'portal_library.index'),
        ('Tuition & Balance', 'bi-cash-coin', 'portal_student.tuition'),
        ('Announcements', 'bi-megaphone', 'portal_news.index'),],
    'admin': [
        ('Dashboard', 'bi-speedometer2', 'admin.dashboard'),
        ('Users', 'bi-people', 'admin_users.index'),
        ('Pending Students', 'bi-person-check', 'admin_pending.index'),
        ('Terms & Admission', 'bi-calendar-range', 'admin_terms.index'),
        ('Announcements', 'bi-megaphone', 'admin_announcements.index'),
        ('Landing Page', 'bi-window', 'admin_landing.index'),
        ('Archive', 'bi-archive', 'admin_archive.index'),
        ('Reports', 'bi-file-earmark-spreadsheet', 'admin_reports.index'),
        ('Audit Logs', 'bi-clipboard-data', 'admin_audit.index'),
        ('Security', 'bi-shield-exclamation', 'admin_security.index'),
        ('Trash Bin', 'bi-trash', 'admin_trash.index'),
        ('Email Log', 'bi-envelope-paper', 'admin_emails.index'),
        ('System Settings', 'bi-sliders', 'admin_settings.index'),],
    'registrar': [
        ('Dashboard', 'bi-speedometer2', 'registrar.dashboard'),
        ('Applications', 'bi-inboxes', 'registrar_applications.index'),
        ('Admission', 'bi-calendar-range', 'registrar_admission.index'),
        ('Enrollment', 'bi-card-checklist', 'registrar_cor.index'),
        ('Student Records', 'bi-folder2-open', 'registrar_records.index'),
        ('Class Schedule', 'bi-calendar3', 'registrar_classes.index'),
        ('Faculty', 'bi-person-badge', 'registrar_faculty.index'),
        ('Curriculum', 'bi-journal-bookmark', 'registrar_curriculum.index'),
        ('Announcements', 'bi-megaphone', 'registrar_announcements.index'),
        ('Landing Page', 'bi-window', 'registrar_landing.index'),
        ('Reports', 'bi-file-earmark-spreadsheet', 'registrar_reports.index'),
        ('Archive', 'bi-archive', 'registrar_archive.index'),],
    'finance': [
        ('Dashboard', 'bi-speedometer2', 'finance.dashboard'),
        ('Quotation Queue', 'bi-receipt', 'finance_queue.index'),
        ('Student Records', 'bi-folder2-open', 'finance_records.index'),
        ('Reports', 'bi-file-earmark-spreadsheet', 'finance_reports.index'),
        ('Announcements', 'bi-megaphone', 'finance_announcements.index'),],
    'faculty': [
        ('Dashboard', 'bi-speedometer2', 'faculty.dashboard'),
        ('My Classes', 'bi-easel', 'faculty_classes.index'),
        ('Announcements', 'bi-megaphone', 'faculty_news.index'),],
}

ACCOUNT_MENU = [('Settings', 'bi-gear', 'account.settings')]


def menu_for(role):
    return MENUS.get(role, [])