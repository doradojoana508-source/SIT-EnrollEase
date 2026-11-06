import os
import uuid
from urllib.parse import urlparse
from flask import current_app
from werkzeug.utils import secure_filename
from db import query, execute
from models.grade import Grade

ZIP = b'PK\x03\x04'
OLE = bytes.fromhex('D0CF11E0A1B11AE1')
OFFICE = 'application/vnd.openxmlformats-officedocument.'


class LmsMaterial:
    """Mga e-book, handout at link ng bawat klase. Ang professor ang nagma-manage; nakikita ng student ang sa klase niya."""

    MAX_BYTES = 30 * 1024 * 1024
    # ext: (laman sa simula ng file, mime, puwedeng buksan sa browser, icon)
    TYPES = {
        'pdf': (b'%PDF', 'application/pdf', True, 'bi-file-earmark-pdf'),
        'epub': (ZIP, 'application/epub+zip', False, 'bi-book'),
        'docx': (ZIP, OFFICE + 'wordprocessingml.document', False, 'bi-file-earmark-word'),
        'pptx': (ZIP, OFFICE + 'presentationml.presentation', False, 'bi-file-earmark-slides'),
        'xlsx': (ZIP, OFFICE + 'spreadsheetml.sheet', False, 'bi-file-earmark-excel'),
        'doc': (OLE, 'application/msword', False, 'bi-file-earmark-word'),
        'ppt': (OLE, 'application/vnd.ms-powerpoint', False, 'bi-file-earmark-slides'),
        'xls': (OLE, 'application/vnd.ms-excel', False, 'bi-file-earmark-excel'),
        'txt': (None, 'text/plain', False, 'bi-file-earmark-text'),
        'jpg': (b'\xff\xd8\xff', 'image/jpeg', True, 'bi-file-earmark-image'),
        'jpeg': (b'\xff\xd8\xff', 'image/jpeg', True, 'bi-file-earmark-image'),
        'png': (b'\x89PNG', 'image/png', True, 'bi-file-earmark-image'),
    }
    ALLOWED_TEXT = 'PDF, EPUB, Word, PowerPoint, Excel, TXT, JPG or PNG'

    # ---------- file sa disk ----------
    @staticmethod
    def folder(class_id):
        path = os.path.join(current_app.root_path, 'uploads', 'lms', str(class_id))
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def remove_file(cls, row):
        """Binubura ang file sa disk (gagamitin ng Trash Bin kapag pinurga na)."""
        if row.get('stored_name'):
            try:
                os.remove(os.path.join(cls.folder(row['class_id']), row['stored_name']))
            except OSError:
                pass

    @classmethod
    def _store(cls, class_id, file):
        """Sine-save ang upload. Ibinabalik ang (info, error)."""
        ext = os.path.splitext(file.filename)[1].lstrip('.').lower()
        if ext not in cls.TYPES:
            return None, f'Only {cls.ALLOWED_TEXT} files are allowed.'
        stream = file.stream
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(0)
        if size == 0:
            return None, 'The file is empty.'
        if size > cls.MAX_BYTES:
            return None, f'The file is too large. The maximum is {cls.MAX_BYTES // (1024 * 1024)} MB.'
        head = stream.read(2048)
        stream.seek(0)
        signature, mime = cls.TYPES[ext][0], cls.TYPES[ext][1]
        if signature is not None and not head.startswith(signature):
            return None, 'That file does not match its type. Upload a real file.'
        if signature is None and b'\x00' in head:
            return None, 'That file does not match its type. Upload a real file.'
        stored = f'{uuid.uuid4().hex}.{ext}'                     # random na pangalan, hindi ang pangalan ng user
        file.save(os.path.join(cls.folder(class_id), stored))
        original = secure_filename(file.filename) or f'material.{ext}'
        return {'stored_name': stored, 'original_name': original[:150], 'mime_type': mime, 'size_bytes': size}, None

    # ---------- pagbasa ----------
    @staticmethod
    def size_label(size):
        if size is None:
            return ''
        if size >= 1024 * 1024:
            return f'{size / (1024 * 1024):.1f} MB'
        return f'{max(1, round(size / 1024))} KB'

    @classmethod
    def _decorate(cls, row):
        row['icon'], row['inline'], row['size_text'] = 'bi-link-45deg', False, ''
        if row['kind'] == 'File':
            ext = row['stored_name'].rsplit('.', 1)[-1]
            row['icon'], row['inline'] = cls.TYPES[ext][3], cls.TYPES[ext][2]
            row['size_text'] = cls.size_label(row['size_bytes'])
        return row

    @classmethod
    def for_class(cls, class_id):
        rows = query("SELECT * FROM lms_materials WHERE class_id = %s AND deleted_at IS NULL "
                     "ORDER BY created_at DESC, id DESC", (class_id,))
        return [cls._decorate(r) for r in rows]

    @classmethod
    def find(cls, material_id):
        row = query("SELECT * FROM lms_materials WHERE id = %s AND deleted_at IS NULL", (material_id,), one=True)
        return cls._decorate(row) if row else None

    # ---------- para sa student ----------
    IN_COR = ("EXISTS (SELECT 1 FROM cor_subjects cs JOIN cors r ON r.id = cs.cor_id "
              "WHERE cs.class_id = m.class_id AND r.user_id = %s)")

    @classmethod
    def for_student(cls, user_id):
        """Mga term -> klase -> materyales, para sa mga klase sa COR ng student (ang visible lang)."""
        rows = query(
            "SELECT m.*, c.title AS class_title, s.code, t.id AS term_id, t.term_no, t.academic_year "
            "FROM lms_materials m JOIN classes c ON c.id = m.class_id JOIN subjects s ON s.id = c.subject_id "
            "JOIN academic_terms t ON t.id = c.term_id "
            f"WHERE m.deleted_at IS NULL AND m.is_visible = 1 AND {cls.IN_COR} "
            "ORDER BY t.academic_year DESC, t.term_no DESC, s.code, m.created_at DESC, m.id DESC", (user_id,))
        terms, by_term, by_class = [], {}, {}
        for r in rows:
            cls._decorate(r)
            if r['term_id'] not in by_term:
                by_term[r['term_id']] = {'label': Grade.term_label(r['term_no'], r['academic_year']), 'classes': []}
                terms.append(by_term[r['term_id']])
            if r['class_id'] not in by_class:
                by_class[r['class_id']] = {'code': r['code'], 'title': r['class_title'], 'materials': []}
                by_term[r['term_id']]['classes'].append(by_class[r['class_id']])
            by_class[r['class_id']]['materials'].append(r)
        return terms

    @classmethod
    def student_find(cls, material_id, user_id):
        row = query(f"SELECT m.* FROM lms_materials m WHERE m.id = %s AND m.deleted_at IS NULL "
                    f"AND m.is_visible = 1 AND {cls.IN_COR}", (material_id, user_id), one=True)
        return cls._decorate(row) if row else None

    # ---------- pagsusuri ----------
    @staticmethod
    def clean_link(link):
        parsed = urlparse(link)
        if len(link) > 500:
            return 'The link must not be longer than 500 characters.'
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            return 'Enter a full link that starts with http:// or https://.'
        return None

    @staticmethod
    def clean(form):
        data, errors = {}, []
        title = ' '.join(form.get('title', '').split())
        if not 3 <= len(title) <= 150:
            errors.append('The title must be 3 to 150 characters.')
        data['title'] = title
        description = ' '.join(form.get('description', '').split())
        if len(description) > 500:
            errors.append('The description must not be longer than 500 characters.')
        data['description'] = description or None
        data['is_visible'] = 1 if form.get('is_visible') == '1' else 0
        return data, errors

    # ---------- pag-save ----------
    @classmethod
    def add(cls, class_id, form, file, by_user):
        """Ibinabalik ang (material_id, errors)."""
        data, errors = cls.clean(form)
        link = form.get('link_url', '').strip()
        has_file = file is not None and bool(file.filename)
        if has_file and link:
            errors.append('Upload a file or paste a link, not both.')
        elif not has_file and not link:
            errors.append('Choose a file to upload or paste a link.')
        elif link and cls.clean_link(link):
            errors.append(cls.clean_link(link))
        if errors:
            return None, errors
        info = None
        if has_file:
            info, error = cls._store(class_id, file)
            if error:
                return None, [error]
        values = [class_id, data['title'], data['description'], 'File' if info else 'Link',
                  info['original_name'] if info else None, info['stored_name'] if info else None,
                  info['mime_type'] if info else None, info['size_bytes'] if info else None,
                  None if info else link, data['is_visible'], by_user.id]
        material_id = execute(
            "INSERT INTO lms_materials (class_id, title, description, kind, original_name, stored_name, mime_type, "
            "size_bytes, link_url, is_visible, uploaded_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            values)
        return material_id, []

    @classmethod
    def update(cls, row, form, file):
        """Ibinabalik ang errors."""
        data, errors = cls.clean(form)
        link = form.get('link_url', '').strip()
        has_file = file is not None and bool(file.filename)
        if row['kind'] == 'Link':
            if not link:
                errors.append('Enter the link.')
            elif cls.clean_link(link):
                errors.append(cls.clean_link(link))
        if errors:
            return errors
        if row['kind'] == 'Link':
            execute("UPDATE lms_materials SET title = %s, description = %s, is_visible = %s, link_url = %s "
                    "WHERE id = %s", (data['title'], data['description'], data['is_visible'], link, row['id']))
            return []
        if has_file:
            info, error = cls._store(row['class_id'], file)
            if error:
                return [error]
            execute("UPDATE lms_materials SET title = %s, description = %s, is_visible = %s, original_name = %s, "
                    "stored_name = %s, mime_type = %s, size_bytes = %s WHERE id = %s",
                    (data['title'], data['description'], data['is_visible'], info['original_name'],
                     info['stored_name'], info['mime_type'], info['size_bytes'], row['id']))
            cls.remove_file(row)
            return []
        execute("UPDATE lms_materials SET title = %s, description = %s, is_visible = %s WHERE id = %s",
                (data['title'], data['description'], data['is_visible'], row['id']))
        return []

    @staticmethod
    def set_visible(material_id, visible):
        execute("UPDATE lms_materials SET is_visible = %s WHERE id = %s", (1 if visible else 0, material_id))

    @staticmethod
    def delete(material_id):
        """Itinatago lang (soft delete). Ang file ay nananatili hanggang purgahin ng Trash Bin."""
        execute("UPDATE lms_materials SET deleted_at = NOW() WHERE id = %s", (material_id,))

    # ---------- abiso ----------
    @staticmethod
    def notify_students(class_id, code, title):
        """Dashboard notice sa lahat ng student sa klase. Ibinabalik ang bilang."""
        total = query("SELECT COUNT(DISTINCT r.user_id) AS n FROM cor_subjects cs JOIN cors r ON r.id = cs.cor_id "
                      "WHERE cs.class_id = %s", (class_id,), one=True)['n']
        if total:
            execute("INSERT INTO notifications (user_id, title, message) "
                    "SELECT DISTINCT r.user_id, 'New class material', %s FROM cor_subjects cs "
                    "JOIN cors r ON r.id = cs.cor_id WHERE cs.class_id = %s",
                    (f'{code}: {title}'[:500], class_id))
        return total