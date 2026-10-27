from models.base import BaseModel


class DocumentType(BaseModel):
    table = 'document_types'

    @classmethod
    def active(cls):
        return cls.run("SELECT * FROM document_types WHERE is_active = 1 ORDER BY id", fetch='all')
    