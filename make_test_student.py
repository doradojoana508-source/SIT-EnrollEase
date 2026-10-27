import sys
from app import app
from models.user import User

if len(sys.argv) < 2:
    sys.exit('Usage: python make_test_student.py your.email@gmail.com')

with app.app_context():
    user = User.find_by_login('23-1-0001')
    if user is None:
        user = User('Test', 'Student', sys.argv[1], 'student')
        user.username = '23-1-0001'          # Student ID
        user.set_password('03/05/17')        # birthday, format YY/MM/DD
        user.is_activated = 0                # hindi makaka-login hangga't walang activation link
        user.save()
    print('Activation link (valid for 7 days):')
    print(f"http://127.0.0.1:5000/auth/activate/{user.get_token('activate')}")