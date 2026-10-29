import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
from db import query, execute

MAX_BYTES = 5 * 1024 * 1024                                   # 5 MB bawat file
# Sinusuri ang laman ng file (hindi lang ang extension), para hindi makalusot ang pekeng file
SIGNATURES = {'pdf': b'%PDF', 'jpg': b'\xff\xd8\xff', 'jpeg': b'\xff\xd8\xff', 'png': b'\x89PNG\r\n\x1a\n'}
MIME = {'pdf': 'application/pdf', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png'}


class ApplicationDocument:
    MAX_BYTES = MAX_BYTES

    @staticmethod
    def folder(application_id):
        path = os.path.join(current_app.root_path, 'uploads', 'applications', str(application_id))
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def for_application(application_id):
        """Dictionary: document_type_id -> row ng na-upload."""
        rows = query("SELECT * FROM application_documents WHERE application_id = %s", (application_id,))
        return {r['document_type_id']: r for r in rows}

    @classmethod
    def store(cls, application_id, type_id, file):
        """Nagse-save ng upload (bago o kapalit). Ibinabalik ang (ok, mensahe)."""
        if file is None or not file.filename:
            return False, 'Choose a file to upload.'
        original = secure_filename(file.filename) or 'document'
        ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
        if ext not in SIGNATURES:
            return False, 'Only PDF, JPG or PNG files are allowed.'
        data = file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return False, f'The file is too large. The maximum is {MAX_BYTES // (1024 * 1024)} MB.'
        if not data.startswith(SIGNATURES[ext]):
            return False, 'That file does not match its type. Upload a real PDF, JPG or PNG.'

        folder = cls.folder(application_id)
        stored = f'{uuid.uuid4().hex}.{ext}'                    # random na pangalan, hindi ang pangalan ng user
        with open(os.path.join(folder, stored), 'wb') as handle:
            handle.write(data)

        old = query("SELECT stored_name FROM application_documents WHERE application_id = %s AND document_type_id = %s",
                    (application_id, type_id), one=True)
        values = (stored, original[:150], MIME[ext], len(data), application_id, type_id)
        if old:
            execute("UPDATE application_documents SET stored_name=%s, original_name=%s, mime_type=%s, size_bytes=%s, "
                    "status='Uploaded', remarks=NULL WHERE application_id=%s AND document_type_id=%s", values)
            cls._remove_file(folder, old['stored_name'])
        else:
            execute("INSERT INTO application_documents (stored_name, original_name, mime_type, size_bytes, "
                    "application_id, document_type_id) VALUES (%s, %s, %s, %s, %s, %s)", values)
        return True, 'File uploaded.'

    @classmethod
    def remove(cls, application_id, type_id):
        old = query("SELECT stored_name FROM application_documents WHERE application_id = %s AND document_type_id = %s",
                    (application_id, type_id), one=True)
        if old:
            execute("DELETE FROM application_documents WHERE application_id = %s AND document_type_id = %s",
                    (application_id, type_id))
            cls._remove_file(cls.folder(application_id), old['stored_name'])

    @staticmethod
    def _remove_file(folder, stored_name):
        try:
            os.remove(os.path.join(folder, stored_name))
        except OSError:
            pass