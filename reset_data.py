"""Ibabalik sa ZERO ang system para sa bagong testing. TEST LANG ITO, huwag gamitin kapag may totoong data na.

Binubura:  lahat ng account maliban sa Admin, applications at documents, interviews, notifications,
           enrollments, quotations, payments, klase, COR, grades, TOR details at audit logs.
Iniiwan:   ang Admin account, Terms, Programs, Subjects, Curriculum, Document Types at Settings.
"""
import os
from db import get_connection

WIPE = ['application_documents', 'applications', 'interviews', 'notifications', 'enrollments', 'quotations',
        'payments', 'faculty_profiles', 'cor_subjects', 'cors', 'lms_materials', 'classes', 'grades', 'attendance', 'tor_info', 'announcements', 'audit_logs']


def main():
    print(__doc__)
    if input('I-type ang RESET para ituloy: ').strip() != 'RESET':
        print('Kinansela. Walang nabago.')
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in WIPE:
        cur.execute("SHOW TABLES LIKE %s", (table,))
        if cur.fetchall():
            cur.execute(f"TRUNCATE TABLE `{table}`")
            print(f'  nalinis: {table}')
    cur.execute("DELETE FROM users WHERE role <> 'admin'")
    print(f'  binura ang {cur.rowcount} na account (nanatili ang Admin)')
    cur.execute("ALTER TABLE users AUTO_INCREMENT = 1")
    cur.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE role = 'admin'")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    conn.close()

    removed = 0
    for folder, _dirs, files in os.walk('uploads'):
        for name in files:
            if name != '.gitkeep':
                os.remove(os.path.join(folder, name))
                removed += 1
    print(f'  binura ang {removed} na na-upload na file')
    print('Tapos na. Bumalik na sa zero ang system.')


if __name__ == '__main__':
    main()