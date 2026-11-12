from db import query


class Curriculum:
    """Ang Programs of Study: ang mga subject ng bawat program."""

    GROUPS = (
        ('Core', 'Required subjects', ''),
        ('Thesis', 'Thesis track', 'Choose the Thesis track or the Project track.'),
        ('Project', 'Project track', 'Choose the Thesis track or the Project track.'),
        ('Elective', 'Electives', 'The student chooses from this list.'),
    )
    # Mga unit na manggagaling pa sa elective (9) at thesis (6) ng Master
    EXTRA_UNITS = {'MACE': 15, 'MACM': 15}

    @classmethod
    def programs(cls):
        rows = query(
            "SELECT p.id, p.code, p.name, p.level, p.total_units, COUNT(c.id) AS subjects, "
            "COALESCE(SUM(CASE WHEN c.grp = 'Core' THEN c.units END), 0) AS core_units "
            "FROM programs p LEFT JOIN curriculum c ON c.program_id = p.id "
            "WHERE p.is_active = 1 GROUP BY p.id, p.code, p.name, p.level, p.total_units ORDER BY p.id")
        for r in rows:
            r['core_units'] = int(r['core_units'])
            r['expected'] = r['core_units'] + cls.EXTRA_UNITS.get(r['code'], 0)
            r['matches'] = (
    r['subjects'] > 0
    and (
        r['expected'] == r['total_units']
        or r['code'] == 'BThCE'
    )
)
        return rows

    @staticmethod
    def program(program_id):
        return query("SELECT * FROM programs WHERE id = %s AND is_active = 1", (program_id,), one=True)

    @classmethod
    def groups(cls, program_id):
        rows = query("SELECT c.seq, c.grp, c.title, c.units, s.code FROM curriculum c "
                     "JOIN subjects s ON s.id = c.subject_id WHERE c.program_id = %s ORDER BY c.seq", (program_id,))
        groups = []
        for key, label, note in cls.GROUPS:
            subjects = [r for r in rows if r['grp'] == key]
            if subjects:
                groups.append({'key': key, 'label': label, 'note': note, 'subjects': subjects,
                               'units': sum(r['units'] for r in subjects)})
        return groups