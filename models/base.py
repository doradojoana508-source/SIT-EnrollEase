from db import get_connection


class BaseModel:
    """Magulang ng lahat ng model: pinagsasaluhang database methods."""
    table = None                       # ibibigay ng bawat anak na class

    @staticmethod
    def run(sql, params=(), fetch=None):
        """Nagpapatakbo ng SQL gamit ang %s placeholders (ligtas sa SQL injection)."""
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            if fetch == 'one':
                return cur.fetchone()
            if fetch == 'all':
                return cur.fetchall()
            conn.commit()
            if sql.lstrip().upper().startswith('INSERT'):
                return cur.lastrowid
            return cur.rowcount
        finally:
            cur.close()
            conn.close()

    @classmethod
    def find_by_id(cls, record_id):
        return cls.run(f"SELECT * FROM {cls.table} WHERE id = %s", (record_id,), fetch='one')

    @classmethod
    def all(cls):
        return cls.run(f"SELECT * FROM {cls.table} ORDER BY id", fetch='all')

    @classmethod
    def delete(cls, record_id):
        return cls.run(f"DELETE FROM {cls.table} WHERE id = %s", (record_id,))

    @classmethod
    def count(cls, where='1=1', params=()):
        row = cls.run(f"SELECT COUNT(*) AS total FROM {cls.table} WHERE {where}", params, fetch='one')
        return row['total']