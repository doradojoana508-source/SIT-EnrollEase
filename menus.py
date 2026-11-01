ROLE_LABELS = {
    'applicant': 'Applicant', 'student': 'Student', 'admin': 'Administrator',
    'registrar': 'Registrar', 'finance': 'Finance', 'faculty': 'Faculty',
}

# (label, bootstrap icon, endpoint). Dadagdagan natin ito sa bawat susunod na hakbang.
MENUS = {
    'applicant': [
        ('Dashboard', 'bi-speedometer2', 'applicant.dashboard'),
        ('My Application', 'bi-journal-text', 'applicant.application'),
        ('Documents', 'bi-folder2-open', 'applicant.documents'),],
    'student':   [('Dashboard', 'bi-speedometer2', 'portal.dashboard')],
    'admin': [
        ('Dashboard', 'bi-speedometer2', 'admin.dashboard'),
        ('Users', 'bi-people', 'admin_users.index'),
        ('Terms & Admission', 'bi-calendar-range', 'admin_terms.index'),
        ('Archive', 'bi-archive', 'admin_archive.index'),
        ('Audit Logs', 'bi-clipboard-data', 'admin_audit.index'),],
    'registrar': [
        ('Dashboard', 'bi-speedometer2', 'registrar.dashboard'),
        ('Applications', 'bi-inboxes', 'registrar_applications.index'),
        ('Admission', 'bi-calendar-range', 'registrar_admission.index'),
        ('Archive', 'bi-archive', 'registrar_archive.index'),],
    'finance':   [('Dashboard', 'bi-speedometer2', 'finance.dashboard')],
    'faculty':   [('Dashboard', 'bi-speedometer2', 'faculty.dashboard')],
}

ACCOUNT_MENU = [('Change Password', 'bi-key', 'account.change_password')]


def menu_for(role):
    return MENUS.get(role, [])