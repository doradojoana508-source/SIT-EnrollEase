from datetime import datetime, timedelta
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
from models.base import BaseModel
from db import query, execute


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
        self.username = None                 # Student ID para sa mga student
        self.role = role
        self.photo = None
        self.is_verified = 0                 # na-verify na ba ang email
        self.is_active = 1                   # 0 = na-deactivate ng Admin
        self.is_activated = 1                # 0 = hindi pa gumagamit ng activation link
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

    # ---- lockout at login record ----
    def is_locked(self):
        return self.locked_until is not None and self.locked_until > datetime.now()

    def register_failed_login(self, max_attempts=5, minutes=15):
        """Bawat maling password ay binibilang. Sa ika-5, naka-lock ang account nang 15 minuto."""
        self.failed_attempts += 1
        if self.failed_attempts >= max_attempts:
            self.locked_until = datetime.now() + timedelta(minutes=minutes)
            self.failed_attempts = 0
        self.run("UPDATE users SET failed_attempts=%s, locked_until=%s WHERE id=%s",
                 (self.failed_attempts, self.locked_until, self.id))

    def record_login(self):
        self.failed_attempts = 0
        self.locked_until = None
        self.run("UPDATE users SET failed_attempts=0, locked_until=NULL, last_login=NOW() WHERE id=%s",
                 (self.id,))

    def activate(self):
        """Ang activation link ay nagpapatunay din na sa kanya ang email."""
        self.is_activated = 1
        self.is_verified = 1
        self.run("UPDATE users SET is_activated=1, is_verified=1 WHERE id=%s", (self.id,))
    
    def mark_verified(self):
        self.is_verified = 1
        self.run("UPDATE users SET is_verified=1 WHERE id=%s", (self.id,))
    
    # ---- token para sa activation at verification link ----
    def get_token(self, purpose):
        """Pirmadong token (gamit ang SECRET_KEY). Hindi puwedeng hulaan o gawin ng iba."""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'id': self.id}, salt=purpose)

    @classmethod
    def from_token(cls, token, purpose, max_age=86400):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = serializer.loads(token, salt=purpose, max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
        return cls.find(data['id'])
    
        # ---- token ng reset: namamatay kapag napalitan na ang password ----
    def get_reset_token(self):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'id': self.id, 'fp': self.__password_hash[-10:]}, salt='reset')

    @classmethod
    def from_reset_token(cls, token, max_age=3600):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = serializer.loads(token, salt='reset', max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
        user = cls.find(data['id'])
        if user is None or user.__password_hash[-10:] != data['fp']:
            return None                       # nagamit na ang link, nagbago na ang password
        return user

    # ---- database ----
    def save(self):
        """INSERT kung bago, UPDATE kung mayroon nang id."""
        if self.id is None:
            self.id = self.run(
                "INSERT INTO users (email, username, password_hash, role, first_name, middle_name, "
                "last_name, is_activated) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (self.email, self.username, self.__password_hash, self.role, self.first_name,
                 self.middle_name, self.last_name, self.is_activated))
        else:
            self.run(
                "UPDATE users SET email=%s, username=%s, password_hash=%s, role=%s, first_name=%s, "
                "middle_name=%s, last_name=%s, photo=%s, is_verified=%s, is_active=%s, is_activated=%s, "
                "failed_attempts=%s, locked_until=%s, session_version=%s WHERE id=%s",
                (self.email, self.username, self.__password_hash, self.role, self.first_name,
                 self.middle_name, self.last_name, self.photo, self.is_verified, self.is_active,
                 self.is_activated, self.failed_attempts, self.locked_until, self.session_version,
                 self.id))
        return self

    @classmethod
    def from_row(cls, row):
        user = cls(row['first_name'], row['last_name'], row['email'], row['role'],
                   row['middle_name'], row['id'], row['password_hash'])
        user.username = row['username']
        user.photo = row['photo']
        user.is_verified = row['is_verified']
        user.is_active = row['is_active']
        user.is_activated = row['is_activated']
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

    @classmethod
    def find_by_login(cls, identifier):
        """Hinahanap gamit ang email (applicant at staff) O ang Student ID (student)."""
        identifier = identifier.strip().lower()
        row = cls.run("SELECT * FROM users WHERE email = %s OR username = %s",
                      (identifier, identifier), fetch='one')
        return cls.from_row(row) if row else None
    
        # ---------- Para sa Admin: paghahanap at mga aksyon ----------
    @classmethod
    def search(cls, q='', role='', limit=10, offset=0):
        """Ibinabalik ang (listahan ng User, kabuuang bilang). Ang values ay parameterized."""
        where, params = [], []
        if q:
            like = f'%{q}%'
            where.append("(first_name LIKE %s OR last_name LIKE %s OR email LIKE %s OR username LIKE %s)")
            params += [like, like, like, like]
        if role:
            where.append("role = %s")
            params.append(role)
        clause = ('WHERE ' + ' AND '.join(where)) if where else ''
        total = query(f"SELECT COUNT(*) AS n FROM users {clause}", params, one=True)['n']
        rows = query(
            f"SELECT * FROM users {clause} ORDER BY id DESC LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        return [cls.from_row(r) for r in rows], total

    @classmethod
    def find_by_username(cls, username):
        row = query("SELECT * FROM users WHERE username = %s", (username,), one=True)
        return cls.from_row(row) if row else None

    def update_details(self, first, middle, last, email):
        execute("UPDATE users SET first_name=%s, middle_name=%s, last_name=%s, email=%s WHERE id=%s",
                (first, middle, last, email, self.id))

    def set_active(self, flag):
        # Tumataas ang session_version, kaya ma-logout agad kapag na-deactivate
        execute("UPDATE users SET is_active=%s, session_version=session_version+1 WHERE id=%s",
                (1 if flag else 0, self.id))

    def force_logout(self):
        execute("UPDATE users SET session_version=session_version+1 WHERE id=%s", (self.id,))

    def unlock(self):
        execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=%s", (self.id,))

    def promote_to_student(self, student_id, initial_password):
        """Ang applicant account ay nagiging student account (parehong email, iisang row)."""
        self.set_password(initial_password)
        execute(
            "UPDATE users SET role='student', username=%s, password_hash=%s, is_activated=0, "
            "session_version=session_version+1 WHERE id=%s",
            (student_id, self.__password_hash, self.id),
        )