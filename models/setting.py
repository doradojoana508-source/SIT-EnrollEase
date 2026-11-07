from models.base import BaseModel


class Setting(BaseModel):
    table = 'settings'

    # key, label, default, pinakamababa, pinakamataas, unit, paliwanag. Ang Admin ang nag-e-edit nito sa Settings page.
    FIELDS = [
        ('Security', [
            ('max_failed_logins', 'Wrong passwords before an account is locked', 5, 3, 10, 'attempts',
             'Applies to every login page.'),
            ('lock_minutes', 'How long a locked account stays locked', 15, 5, 120, 'minutes',
             'The Administrator can unlock an account sooner under Security.'),
            ('ip_limit', 'Failed logins before an IP address is blocked', 10, 5, 50, 'attempts',
             'Counts every account tried from the same IP address. Not applied to the Administrator login or to 127.0.0.1.'),
            ('ip_window', 'Time window for the IP address count and block', 15, 5, 120, 'minutes', ''),
        ]),
        ('Records', [
            ('trash_days', 'Days a deleted item stays in the Trash Bin', 30, 7, 90, 'days',
             'After this, it is deleted for good.'),
            ('email_log_days', 'Days the Email Log is kept', 180, 30, 365, 'days', ''),
            ('security_log_days', 'Days the Security events are kept', 90, 30, 365, 'days', ''),
        ]),
        ('Uploads', [
            ('material_max_mb', 'Largest class material file', 30, 1, 30, 'MB',
             'The server accepts at most 32 MB per upload, so 30 MB is the highest value.'),
        ]),
    ]

    @classmethod
    def as_dict(cls):
        """Ibinabalik ang lahat ng setting bilang dictionary: {'school_phone': '049-...', ...}"""
        rows = cls.run("SELECT setting_key, setting_value FROM settings", fetch='all')
        return {row['setting_key']: row['setting_value'] for row in rows}

    @classmethod
    def number(cls, key, default, lo=None, hi=None):
        """Ang numerong setting, o ang default kung wala o sira. Nasa pagitan ng lo at hi."""
        try:
            row = cls.run("SELECT setting_value FROM settings WHERE setting_key = %s", (key,), fetch='one')
            value = int(row['setting_value']) if row else default
        except Exception:
            value = default
        if lo is not None:
            value = max(lo, value)
        if hi is not None:
            value = min(hi, value)
        return value

    @classmethod
    def numbers(cls):
        """Lahat ng numerong setting para sa form: {key: kasalukuyang halaga}."""
        return {key: cls.number(key, default, lo, hi)
                for _group, fields in cls.FIELDS for key, _label, default, lo, hi, _unit, _help in fields}

    @classmethod
    def clean_numbers(cls, form):
        data, errors = {}, []
        for _group, fields in cls.FIELDS:
            for key, label, default, lo, hi, unit, _help in fields:
                raw = form.get(key, '').strip()
                if not raw.isdigit() or not lo <= int(raw) <= hi:
                    errors.append(f'{label}: enter a whole number from {lo} to {hi}.')
                else:
                    data[key] = int(raw)
        return data, errors

    @classmethod
    def save_numbers(cls, data):
        for key, value in data.items():
            cls.run("INSERT INTO settings (setting_key, setting_value) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)", (key, str(value)))

    @classmethod
    def restore_numbers(cls):
        keys = [key for _group, fields in cls.FIELDS for key, *_ in fields]
        cls.run("DELETE FROM settings WHERE setting_key IN (%s)" % ','.join(['%s'] * len(keys)), keys)


class Number:
    """Class attribute na laging kinukuha ang pinakabagong halaga mula sa Settings.
    Halimbawa: DAYS = Number('trash_days', 30, 7, 90). Kaya gumagana pa rin ang Trash.DAYS sa buong code."""

    def __init__(self, key, default, lo=None, hi=None, scale=1):
        self.key, self.default, self.lo, self.hi, self.scale = key, default, lo, hi, scale

    def __get__(self, obj, owner=None):
        return Setting.number(self.key, self.default, self.lo, self.hi) * self.scale