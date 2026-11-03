"""Gumagawa ng mga professor ng SIT (pang-test) at ng kanilang profile. Ligtas patakbuhin ulit: nilalaktawan ang meron na.
Gamitin: python seed_faculty.py joanadorado33@gmail.com   (ang email na ito ang pagdadagdagan ng +pangalan)"""
import re
import secrets
import sys
from app import app
from models.faculty import Faculty
from models.user import User

# (unang pangalan, apelyido, title, pangalan sa COR, specialties)
PROFESSORS = [
    ('Jassed', 'Cabrera', 'Prof.', 'Prof. Jassed', 'Church Administration, Music'),
    ('Jon', 'Benosa', 'Dr.', 'Dr. Jon', 'Homiletics, Research, Missions, Christian Education'),
    ('Clarence', 'Palana', 'Ptr.', 'Ptr. Clarence', 'Apologetics, Eschatology'),
    ('Donato', 'de Jesus', 'Rev.', 'Rev. Don', 'Leadership'),
    ('Jaymark', 'Bagacina', 'Ptr.', 'Ptr. Jaymark', 'Old Testament Survey'),
    ('Dave', 'Dalhag', 'Ptr.', 'Ptr. Dave', 'Christian Education'),
    ('Jamie', 'Calagos', 'Ptr.', 'Ptr. Jamie', 'Hebrew'),
    ('Louie', 'Reyes', 'Rev.', 'Rev. Louie', 'Systematic Theology, New Testament Survey, Greek, Leadership'),
]

if len(sys.argv) != 2 or '@' not in sys.argv[1]:
    sys.exit('Usage: python seed_faculty.py your.email@gmail.com')
name, domain = sys.argv[1].lower().split('@')
name = name.split('+')[0]

with app.app_context():
    for first, last, title, display, specialties in PROFESSORS:
        email = f'{name}+{re.sub(r"[^a-z]", "", first.lower())}@{domain}'
        user = User.find_by_email(email)
        if user is None:
            user = User(first, last, email, 'faculty')
            user.set_password(secrets.token_urlsafe(24))
            user.is_activated = 0                      # sila ang pipili ng password sa activation link
            user.save()
            user = User.find_by_email(email)
            print('Created  ', email)
        else:
            print('Existing ', email)
        Faculty.save(user.id, {'title': title, 'display_name': display, 'specialties': specialties})
print('Done. Check Registrar > Faculty.')