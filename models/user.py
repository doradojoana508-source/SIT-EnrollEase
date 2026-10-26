from werkzeug.security import generate_password_hash, check_password_hash
from models.base import BaseModel


class User(BaseModel):
    table = 'users'
    ROLES = ('admin', 'registrar', 'finance', 'faculty', 'student', 'applicant')

    def __init__(self, first_name, last_name, email, role='applicant',
                 middle_name=None, id=None, password_hash=None):
        self.id = id
        self.first_name = first_name
        self.middle_name = middle_name or None
        self.last_name = last_name
        self.email = email.strip().lower()
        self.role = role
        self.photo = None
        self.is_verified = 0
        self.is_active = 1
        self.institutional_email = None
        self.institutional_active = 0
        self.failed_attempts = 0
        self.locked_until = None
        self.session_version = 0
        self.__password_hash = password_hash          # private (encapsulation)

    # ---- mga property ----
    @property
    def full_name(self):
        """Juan Santos Dela Cruz"""
        return ' '.join(p for p in (self.first_name, self.middle_name, self.last_name) if p)

    @property
    def formal_name(self):
        """DELA CRUZ, JUAN S. (gaya ng grade sheet ng SIT)"""
        middle = f" {self.middle_name[0].upper()}." if self.middle_name else ''
        return f"{self.last_name.upper()}, {self.first_name.upper()}{middle}"

    # ---- password ----
    def set_password(self, raw_password):
        self.__password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.__password_hash, raw_password)

    # ---- database ----
    def save(self):
        """INSERT kung bago, UPDATE kung mayroon nang id."""
        if self.id is None:
            self.id = self.run(
                "INSERT INTO users (email, password_hash, role, first_name, middle_name, last_name) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (self.email, self.__password_hash, self.role,
                 self.first_name, self.middle_name, self.last_name))
        else:
            self.run(
                "UPDATE users SET email=%s, password_hash=%s, role=%s, first_name=%s, middle_name=%s, "
                "last_name=%s, photo=%s, is_verified=%s, is_active=%s, institutional_email=%s, "
                "institutional_active=%s, failed_attempts=%s, locked_until=%s, session_version=%s "
                "WHERE id=%s",
                (self.email, self.__password_hash, self.role, self.first_name, self.middle_name,
                 self.last_name, self.photo, self.is_verified, self.is_active,
                 self.institutional_email, self.institutional_active, self.failed_attempts,
                 self.locked_until, self.session_version, self.id))
        return self

    @classmethod
    def from_row(cls, row):
        user = cls(row['first_name'], row['last_name'], row['email'], row['role'],
                   row['middle_name'], row['id'], row['password_hash'])
        user.photo = row['photo']
        user.is_verified = row['is_verified']
        user.is_active = row['is_active']
        user.institutional_email = row['institutional_email']
        user.institutional_active = row['institutional_active']
        user.failed_attempts = row['failed_attempts']
        user.locked_until = row['locked_until']
        user.session_version = row['session_version']
        return user

    @classmethod
    def find(cls, user_id):
        row = cls.find_by_id(user_id)
        return cls.from_row(row) if row else None

    @classmethod
    def find_by_email(cls, email):
        row = cls.run("SELECT * FROM users WHERE email = %s", (email.strip().lower(),), fetch='one')
        return cls.from_row(row) if row else None