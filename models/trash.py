from datetime import datetime
from db import query, execute
from models.lms_material import LmsMaterial
from models.setting import Number


class Trash:
    """Basurahan ng mga binurang nilalaman. 30 araw bago tuluyang mabura.
    Mga anunsyo at materyales lang ang nandito. Ang mga record ng mga student (application, enrollment,
    COR, grade, bayad) ay hindi kailanman napupunta rito, kaya hindi sila mapupurga."""

    DAYS = Number('trash_days', 30, 7, 90)
    # kind: label, table, at ang SQL na naglilista ng mga binura (id, title, deleted_at, owner, detail)
    SOURCES = {
        'announcement': {
            'label': 'Announcement', 'table': 'announcements',
            'sql': "SELECT x.id, x.title, x.deleted_at, COALESCE(CONCAT(u.first_name, ' ', u.last_name), 'Unknown') AS owner, "
                   "CONCAT('For ', x.audience) AS detail FROM announcements x "
                   "LEFT JOIN users u ON u.id = x.created_by WHERE x.deleted_at IS NOT NULL"},
        'material': {
            'label': 'Class material', 'table': 'lms_materials',
            'sql': "SELECT x.id, x.title, x.deleted_at, COALESCE(CONCAT(u.first_name, ' ', u.last_name), 'Unknown') AS owner, "
                   "CONCAT(s.code, ' - ', c.title) AS detail FROM lms_materials x "
                   "JOIN classes c ON c.id = x.class_id JOIN subjects s ON s.id = c.subject_id "
                   "LEFT JOIN users u ON u.id = x.uploaded_by WHERE x.deleted_at IS NOT NULL"},
    }

    @classmethod
    def items(cls, q='', kind=''):
        """Lahat ng nasa basurahan, pinakabago ang nasa itaas."""
        out, needle, now = [], q.lower(), datetime.now()
        for key, src in cls.SOURCES.items():
            if kind and kind != key:
                continue
            for row in query(src['sql']):
                row['kind'], row['label'] = key, src['label']
                row['days_left'] = max(0, cls.DAYS - (now - row['deleted_at']).days)
                if needle and needle not in f"{row['title']} {row['owner']} {row['detail']}".lower():
                    continue
                out.append(row)
        out.sort(key=lambda r: (r['deleted_at'], r['id']), reverse=True)
        return out

    @classmethod
    def counts(cls):
        return {key: query(f"SELECT COUNT(*) AS n FROM {src['table']} WHERE deleted_at IS NOT NULL", one=True)['n']
                for key, src in cls.SOURCES.items()}

    @classmethod
    def find(cls, kind, item_id):
        src = cls.SOURCES.get(kind)
        if src is None:
            return None
        return query(f"SELECT * FROM {src['table']} WHERE id = %s AND deleted_at IS NOT NULL", (item_id,), one=True)

    @classmethod
    def restore(cls, kind, item_id):
        execute(f"UPDATE {cls.SOURCES[kind]['table']} SET deleted_at = NULL WHERE id = %s", (item_id,))

    @classmethod
    def forever(cls, kind, row):
        """Tuluyang binubura ang record (at ang file nito, kung may file)."""
        if kind == 'material':
            LmsMaterial.remove_file(row)
        execute(f"DELETE FROM {cls.SOURCES[kind]['table']} WHERE id = %s", (row['id'],))

    @classmethod
    def empty(cls):
        total = 0
        for kind, src in cls.SOURCES.items():
            for row in query(f"SELECT * FROM {src['table']} WHERE deleted_at IS NOT NULL"):
                cls.forever(kind, row)
                total += 1
        return total

    @classmethod
    def purge_expired(cls):
        """Binubura ang mga lampas na sa 30 araw sa basurahan. Ibinabalik ang bilang."""
        total = 0
        for kind, src in cls.SOURCES.items():
            rows = query(f"SELECT * FROM {src['table']} WHERE deleted_at IS NOT NULL "
                         "AND deleted_at < NOW() - INTERVAL %s DAY", (cls.DAYS,))
            for row in rows:
                cls.forever(kind, row)
                total += 1
        return total