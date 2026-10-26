from models.base import BaseModel


class Program(BaseModel):
    table = 'programs'

    @classmethod
    def active(cls):
        """Mga program na bukas para sa application."""
        return cls.run("SELECT * FROM programs WHERE is_active = 1 ORDER BY id", fetch='all')