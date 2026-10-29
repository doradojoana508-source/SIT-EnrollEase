import sys
from datetime import datetime, timedelta
from app import app
from models.user import User
from models.application import Application

if len(sys.argv) != 2:
    sys.exit('Usage: python make_test_approval.py <applicant email>')

with app.test_request_context('/', base_url='http://127.0.0.1:5000'):
    user = User.find_by_email(sys.argv[1].lower())
    application = Application.find_by_user(user.id) if user else None
    if application is None:
        sys.exit('No application found for that email.')
    when = (datetime.now() + timedelta(days=3)).replace(hour=9, minute=0, second=0, microsecond=0)
    application.approve(None, {'interviewer': 'Dean', 'scheduled_at': when,
                               'venue': "Registrar's Office", 'notes': 'Please arrive 15 minutes early.'})
    print('Approved. Interview set for', when)