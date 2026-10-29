import sys
import getpass
from app import app
from models.user import User

if len(sys.argv) != 3 or sys.argv[1] not in ('registrar', 'finance', 'faculty'):
    sys.exit('Usage: python make_test_staff.py <registrar|finance|faculty> <email>')

role, email = sys.argv[1], sys.argv[2].lower()
password = getpass.getpass('Password for this test account: ')

with app.app_context():
    if User.find_by_email(email):
        sys.exit('That email already exists.')
    user = User('Test', role.title(), email, role)
    user.set_password(password)
    user.save()
    User.run("UPDATE users SET is_verified=1, is_activated=1 WHERE email=%s", (email,))
    print(f'Created {role} account: {email}')