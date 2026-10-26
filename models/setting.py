from models.base import BaseModel


class Setting(BaseModel):
    table = 'settings'

    @classmethod
    def as_dict(cls):
        """Ibinabalik ang lahat ng setting bilang dictionary: {'school_phone': '049-...', ...}"""
        rows = cls.run("SELECT setting_key, setting_value FROM settings", fetch='all')
        return {row['setting_key']: row['setting_value'] for row in rows}