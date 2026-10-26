from models.base import BaseModel
from models.user import User

run = BaseModel.run

CCF_CCL_OBJECTIVE = ("To help church leaders grow in their leadership calling, and practical ministry "
                     "service as they work harmoniously with the pastors, fellow leaders, and workers "
                     "in caring and feeding the church.")
CERT_PREREQ = ("Must be a Christian and serving in any church leadership capacity "
               "(elder, deacon, council member, or worker).")

# (code, name, level, total_units, objective, prerequisites)
PROGRAMS = [
    ('CCF', 'Certificate in Christian Foundation', 'Certificate', 24, CCF_CCL_OBJECTIVE, CERT_PREREQ),
    ('CCL', 'Certificate in Christian Leadership', 'Certificate', 24, CCF_CCL_OBJECTIVE, CERT_PREREQ),
    ('DPS', 'Diploma in Pastoral Studies', 'Diploma', 54,
     'To provide further training to those who have been called to ministry, equipping them to become '
     'effective leaders and ministers of the gospel in their local churches.',
     'Must complete the Certificate of Christian Foundation or Certificate in Christian Leadership '
     'and has legitimate reason of not pursuing the Bachelor of Theology program.'),
    ('BThPM', 'Bachelor of Theology Major in Pastoral Ministry', 'Bachelor', 144, None, None),
    ('BThCE', 'Bachelor of Theology Major in Christian Education', 'Bachelor', 144, None, None),
    ('MACE', 'Master of Arts in Christian Education', 'Master', 62, None, None),
    ('MACM', 'Master of Arts in Christian Ministry', 'Master', 62, None, None),
    ('MDiv', 'Master of Divinity in New Testament Exegetical Theology', 'Master', 58,
     'A professional graduate degree program designed to train and prepare individuals to demonstrate '
     'a high level of competence in New Testament exegetical theology and specialized educational '
     'teaching ministry.', None),
]

# (name, description)  -- galing sa REQUIREMENTS FOR NEW STUDENTS
DOCUMENT_TYPES = [
    ('Admission Form', 'Signed admission form'),
    ('Testimony of Conversion', 'Written testimony of your conversion'),
    ("Pastor's Recommendation", 'Recommendation letter from your pastor'),
    ('Latest Diploma/Certificate', 'Latest diploma or certificate of last educational attainment'),
    ('2x2 Photo', '2x2 photo with a white background'),
    ('PSA/Birth Certificate', 'Photocopy of PSA/Birth Certificate'),
]

SETTINGS = {
    'application_open': '2026-10-01',
    'application_close': '2026-12-15',
    'institutional_domain': 'sit.edu.ph',
    'school_name': 'Simons Institute of Theology',
    'school_address': '7-108 T. Valdellon St., Paete, Laguna 4016',
    'school_email': 'ntbcpaetefounded1957@yahoo.com',
    'school_phone': '049-557-2464',
}

# (first_name, last_name, email, role)  -- dummy lang; HUWAG gumamit ng totoong pangalan
STAFF = [
    ('System', 'Admin', 'admin@sit.edu.ph', 'admin'),
    ('Test', 'Registrar', 'registrar@sit.edu.ph', 'registrar'),
    ('Test', 'Finance', 'finance@sit.edu.ph', 'finance'),
    ('Test', 'Faculty', 'faculty@sit.edu.ph', 'faculty'),
]
DEV_PASSWORD = 'Password123'          # pang-development lang; papalitan bago i-deploy


def seed_programs():
    for p in PROGRAMS:
        run("INSERT IGNORE INTO programs (code, name, level, total_units, objective, prerequisites) "
            "VALUES (%s, %s, %s, %s, %s, %s)", p)


def seed_documents():
    for d in DOCUMENT_TYPES:
        run("INSERT IGNORE INTO document_types (name, description) VALUES (%s, %s)", d)
    # lahat ng program ay nangangailangan ng lahat ng dokumento para sa New students
    run("INSERT IGNORE INTO program_documents (program_id, document_type_id, applicant_type) "
        "SELECT p.id, d.id, 'New' FROM programs p CROSS JOIN document_types d")


def seed_term_and_settings():
    run("INSERT IGNORE INTO academic_terms (term_no, academic_year, is_current) VALUES (1, '2026-2027', 1)")
    for key, value in SETTINGS.items():
        run("INSERT IGNORE INTO settings (setting_key, setting_value) VALUES (%s, %s)", (key, value))


def seed_staff():
    for first, last, email, role in STAFF:
        if User.find_by_email(email) is None:
            user = User(first, last, email, role)
            user.set_password(DEV_PASSWORD)
            user.save()
            user.is_verified = 1
            user.save()


if __name__ == '__main__':
    seed_programs()
    seed_documents()
    seed_term_and_settings()
    seed_staff()
    print('Seed complete.')
    print('Programs:', run('SELECT COUNT(*) AS n FROM programs', fetch='one')['n'])
    print('Document types:', run('SELECT COUNT(*) AS n FROM document_types', fetch='one')['n'])
    print('Program-document links:', run('SELECT COUNT(*) AS n FROM program_documents', fetch='one')['n'])
    print('Staff users:', run('SELECT COUNT(*) AS n FROM users', fetch='one')['n'])