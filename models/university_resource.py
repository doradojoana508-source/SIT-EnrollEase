import os
import uuid
from urllib.parse import urlparse
from flask import current_app
from werkzeug.utils import secure_filename
from db import query, execute
from models.lms_material import LmsMaterial


class UniversityResource:
    """University-wide documents and links managed by the Admin or Registrar."""

    @staticmethod
    def folder():
        path = os.path.join(current_app.root_path, 'uploads', 'resources')
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def _store(cls, file):
        ext = os.path.splitext(file.filename)[1].lstrip('.').lower()
        if ext not in LmsMaterial.TYPES:
            return None, f'Only {LmsMaterial.ALLOWED_TEXT} files are allowed.'
        stream = file.stream
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(0)
        if size <= 0:
            return None, 'The file is empty.'
        if size > LmsMaterial.MAX_BYTES:
            return None, f'The file is too large. The maximum is {LmsMaterial.MAX_BYTES // (1024 * 1024)} MB.'
        head = stream.read(2048)
        stream.seek(0)
        signature, mime = LmsMaterial.TYPES[ext][0], LmsMaterial.TYPES[ext][1]
        if signature is not None and not head.startswith(signature):
            return None, 'That file does not match its type. Upload a real file.'
        if signature is None and b'\x00' in head:
            return None, 'That file does not match its type. Upload a real file.'
        stored = f'{uuid.uuid4().hex}.{ext}'
        file.save(os.path.join(cls.folder(), stored))
        original = secure_filename(file.filename) or f'resource.{ext}'
        return {'stored_name': stored, 'original_name': original[:150], 'mime_type': mime, 'size_bytes': size}, None

    @staticmethod
    def _decorate(row):
        if row:
            row['size_text'] = LmsMaterial.size_label(row.get('size_bytes'))
            ext = (row.get('stored_name') or '').rsplit('.', 1)[-1].lower()
            row['icon'] = LmsMaterial.TYPES.get(ext, (None, None, False, 'bi-link-45deg'))[3] if row.get('kind') == 'File' else 'bi-link-45deg'
        return row

    @classmethod
    def all(cls):
        return [cls._decorate(r) for r in query(
            "SELECT * FROM university_resources WHERE deleted_at IS NULL ORDER BY category, title")]

    @classmethod
    def active(cls):
        groups = {}
        for row in query("SELECT * FROM university_resources WHERE is_active = 1 AND deleted_at IS NULL "
                         "ORDER BY category, title"):
            cls._decorate(row)
            groups.setdefault(row['category'], []).append(row)
        return groups

    @classmethod
    def find(cls, resource_id):
        return cls._decorate(query("SELECT * FROM university_resources WHERE id = %s AND deleted_at IS NULL",
                                   (resource_id,), one=True))

    @classmethod
    def student_find(cls, resource_id):
        return cls._decorate(query("SELECT * FROM university_resources WHERE id = %s AND is_active = 1 "
                                   "AND deleted_at IS NULL", (resource_id,), one=True))

    @classmethod
    def add(cls, form, file, user_id):
        title = ' '.join((form.get('title') or '').split())
        category = ' '.join((form.get('category') or 'General').split())
        description = ' '.join((form.get('description') or '').split())
        link = (form.get('link_url') or '').strip()
        has_file = file is not None and bool(file.filename)
        errors = []
        if not 3 <= len(title) <= 150:
            errors.append('Title must be 3 to 150 characters.')
        if not 2 <= len(category) <= 60:
            errors.append('Category must be 2 to 60 characters.')
        if len(description) > 500:
            errors.append('Description must not exceed 500 characters.')
        if has_file and link:
            errors.append('Upload a file or provide a link, not both.')
        elif not has_file and not link:
            errors.append('Choose a file or provide a link.')
        elif link:
            error = LmsMaterial.clean_link(link)
            if error:
                errors.append(error)
        if errors:
            return None, errors
        info = None
        if has_file:
            info, error = cls._store(file)
            if error:
                return None, [error]
        resource_id = execute(
            "INSERT INTO university_resources (title, category, description, kind, original_name, stored_name, "
            "mime_type, size_bytes, link_url, is_active, uploaded_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s)",
            (title, category, description or None, 'File' if info else 'Link',
             info['original_name'] if info else None, info['stored_name'] if info else None,
             info['mime_type'] if info else None, info['size_bytes'] if info else None, link or None, user_id))
        return resource_id, []

    @staticmethod
    def set_active(resource_id, active):
        execute("UPDATE university_resources SET is_active = %s WHERE id = %s AND deleted_at IS NULL",
                (1 if active else 0, resource_id))

    @staticmethod
    def delete(resource_id):
        execute("UPDATE university_resources SET deleted_at = NOW(), is_active = 0 "
                "WHERE id = %s AND deleted_at IS NULL", (resource_id,))
