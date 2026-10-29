ROLE_LABELS = {
    'applicant': 'Applicant', 'student': 'Student', 'admin': 'Administrator',
    'registrar': 'Registrar', 'finance': 'Finance', 'faculty': 'Faculty',
}

# (label, bootstrap icon, endpoint). Dadagdagan natin ito sa bawat susunod na hakbang.
MENUS = {
    'applicant': [('Dashboard', 'bi-speedometer2', 'applicant.dashboard')],
    'student':   [('Dashboard', 'bi-speedometer2', 'portal.dashboard')],
    'admin':     [('Dashboard', 'bi-speedometer2', 'admin.dashboard')],
    'registrar': [('Dashboard', 'bi-speedometer2', 'registrar.dashboard')],
    'finance':   [('Dashboard', 'bi-speedometer2', 'finance.dashboard')],
    'faculty':   [('Dashboard', 'bi-speedometer2', 'faculty.dashboard')],
}

ACCOUNT_MENU = [('Change Password', 'bi-key', 'account.change_password')]


def menu_for(role):
    return MENUS.get(role, [])