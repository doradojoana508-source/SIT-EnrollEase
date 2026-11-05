from datetime import time
from db import query, execute
from models.class_offering import ClassOffering
from models.faculty import Faculty


class Scheduler:
    """Ang system ang gumagawa ng klase (schedule at professor). Tentative ito, at ang Registrar ang puwedeng mag-edit."""

    DAY = 'TH'                                    # Huwebes lang ang pasok ng SIT
    SLOTS = ((time(8, 0), time(10, 0)), (time(10, 0), time(12, 0)),
             (time(13, 0), time(15, 0)), (time(17, 0), time(19, 0)))      # 8-10AM, 10-12N, 1-3PM, 5-7PM

    @staticmethod
    def _overlap(a_day, a_start, a_end, b):
        return (a_day == b['day_code'] and a_start < ClassOffering.as_time(b['end_time'])
                and a_end > ClassOffering.as_time(b['start_time']))

    @classmethod
    def _clashes(cls, row, picked):
        start, end = ClassOffering.as_time(row['start_time']), ClassOffering.as_time(row['end_time'])
        return any(cls._overlap(row['day_code'], start, end, p) for p in picked)

    @classmethod
    def place(cls, term_id, item, picked):
        """Ang klase para sa subject na ito. Isang klase lang bawat subject: gagamitin kung bukas na (at hindi
        banggaan sa mga napili na ng student; kung banggaan, lalaktawan ang subject). Kung wala pa, gagawa ng bago sa
        libreng slot ng Huwebes na may professor na tugma."""
        rows = query("SELECT * FROM classes WHERE term_id = %s AND subject_id = %s AND title = %s ORDER BY id",
                     (term_id, item['subject_id'], item['title']))
        if rows:
            return next((r for r in rows if not cls._clashes(r, picked)), None)

        free = [s for s in cls.SLOTS if not any(cls._overlap(cls.DAY, s[0], s[1], p) for p in picked)]
        if not free:
            return None
        slot, teacher = free[0], None
        for start, end in free:                   # unahin ang slot na may professor na tugma at libre
            teacher = Faculty.pick(item['title'], term_id, cls.DAY, start, end)
            if teacher:
                slot = (start, end)
                break
        class_id = execute(
            "INSERT INTO classes (term_id, subject_id, title, units, section, day_code, start_time, end_time, "
            "faculty_id, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Tentative')",
            (term_id, item['subject_id'], item['title'], item['units'], ClassOffering.SECTION, cls.DAY,
             slot[0], slot[1], teacher))
        if teacher:
            ClassOffering._notify_assigned(class_id)
        return query("SELECT * FROM classes WHERE id = %s", (class_id,), one=True)

    @classmethod
    def assign_missing(cls, term_id):
        """Pipiliin ang professor ng lahat ng klaseng wala pa. Ibinabalik ang bilang na nalagyan."""
        done = 0
        for row in query("SELECT * FROM classes WHERE term_id = %s AND faculty_id IS NULL ORDER BY id", (term_id,)):
            teacher = Faculty.pick(row['title'], term_id, row['day_code'],
                                   ClassOffering.as_time(row['start_time']), ClassOffering.as_time(row['end_time']))
            if teacher:
                execute("UPDATE classes SET faculty_id = %s WHERE id = %s", (teacher, row['id']))
                ClassOffering._notify_assigned(row['id'])
                done += 1
        return done