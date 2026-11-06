import os
import re
from datetime import datetime
from flask import current_app
from markupsafe import Markup, escape
from db import query, execute

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class Landing:
    """Nilalaman ng landing page na ine-edit ng Admin at Registrar. May default ang bawat bahagi,
    kaya gumagana ang page kahit wala pang laman ang landing_content."""

    DEFAULTS = {
        'hero_eyebrow': 'WELCOME TO',
        'hero_title': 'SIT-EnrollEase',
        'hero_lead': 'Your journey in theological education starts here. Enroll online, track your '
                     'application and stay connected with the school.',
        'about_quote': 'Faithful in living, faithful in teaching',
        'about_intro': 'SIMONS Institute of Theology is the theological training arm of New Testament Baptist '
                       'Church. It is tasked to train church leaders and workers for the work of ministry, and '
                       'seeks to produce pastors and missionaries for local and international ministries.',
        'vision': "SIMONS Institute of Theology shall be a leading theological institute in modeling Christ's "
                  "life and teaching.",
        'mission': 'SIMONS Institute of Theology shall achieve its vision through Christian life practical '
                   'training, in-depth study of Christian doctrines, and constant Christian discipline.',
        'core_values': 'Deeds: Life that is steered by the Spirit of Christ (Gal. 5:22-26).\n'
                       'Doctrine: Life that is sanctified by the truth of Christ (Jn. 17:17).\n'
                       'Discipline: Life that is surrendered in obedience to Christ (Lk. 9:23).',
        'process_new': '**Create an account** and verify your email address while admission is open.\n'
                       '**Fill out the Admission Form**, choose your program, then print and sign it.\n'
                       '**Upload your requirements** for review by the Registrar.\n'
                       '**Interview** with the Executive Director or the Academic Dean about your ministry call '
                       'and direction.\n'
                       '**Submit your original documents** to the Registrar once you pass the interview.\n'
                       '**Get your tuition quotation** from the Finance office.\n'
                       '**Receive your Certificate of Enrolment** from the Registrar. You are now enrolled.',
        'process_continuing': 'Complete your clearance and give it to the Registrar.\n'
                              'Pre-enroll. The Executive Director or Academic Dean checks your subjects and '
                              'ministry direction.\n'
                              'Get your tuition quotation from the Finance office and settle any balance.\n'
                              'Receive your Certificate of Enrolment from the Registrar.',
        'continuing_note': 'Log in to the Student Portal with your Student ID.',
        'requirements_new': '',                          # blangko = gamitin ang listahan ng Document Types
    }

    # section -> [(key, max haba, kailangan ba, max na linya)]
    SECTIONS = {
        'banner': [('hero_eyebrow', 40, True, 1), ('hero_title', 60, True, 1), ('hero_lead', 300, True, 1)],
        'about': [('about_quote', 150, True, 1), ('about_intro', 900, True, 1), ('vision', 600, True, 1),
                  ('mission', 600, True, 1), ('core_values', 1500, True, 8)],
        'process': [('process_new', 3000, True, 12), ('process_continuing', 2000, True, 10),
                    ('continuing_note', 200, True, 1)],
        'requirements': [('requirements_new', 2000, False, 20)],
    }
    LABELS = {'hero_eyebrow': 'Small text above the title', 'hero_title': 'Title', 'hero_lead': 'Short description',
              'about_quote': 'Motto', 'about_intro': 'About SIT', 'vision': 'Vision', 'mission': 'Mission',
              'core_values': 'Core values', 'process_new': 'Steps for new students and transferees',
              'process_continuing': 'Steps for continuing students and returnees',
              'continuing_note': 'Note above the steps', 'requirements_new': 'Requirements list'}
    LINE_MAX = 300
    IMAGE_TYPES = {'.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff', '.png': b'\x89PNG', '.webp': b'RIFF'}
    IMAGE_MAX = 3 * 1024 * 1024

    # ---------- pagbasa ----------
    @staticmethod
    def lines(text):
        return [ln.strip() for ln in (text or '').splitlines() if ln.strip()]

    @staticmethod
    def rich(text):
        """Ligtas na HTML: **bold** lang ang pinapayagan."""
        return Markup(re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', str(escape(text))))

    @classmethod
    def raw(cls):
        """Ang lahat ng teksto (default + na-edit), para sa mga form."""
        values = dict(cls.DEFAULTS)
        for row in query('SELECT content_key, content_value FROM landing_content'):
            if row['content_key'] in values and (row['content_value'] or '').strip():
                values[row['content_key']] = row['content_value']
            elif row['content_key'] == 'hero_image':
                values['hero_image'] = row['content_value']
        values.setdefault('hero_image', '')
        return values

    @classmethod
    def content(cls):
        """Handa nang gamitin ng landing page."""
        v = cls.raw()
        core = []
        for ln in cls.lines(v['core_values']):
            name, sep, text = ln.partition(':')
            core.append({'name': name.strip(), 'text': text.strip()} if sep else {'name': '', 'text': ln})
        v['core'] = core
        v['steps_new'] = [cls.rich(x) for x in cls.lines(v['process_new'])]
        v['steps_continuing'] = [cls.rich(x) for x in cls.lines(v['process_continuing'])]
        v['requirements'] = cls.lines(v['requirements_new'])          # walang laman = gamitin ang Document Types
        return v

    # ---------- pag-save ----------
    @classmethod
    def clean(cls, section, form):
        data, errors = {}, []
        for key, limit, required, max_lines in cls.SECTIONS[section]:
            text = form.get(key, '').replace('\r', '').strip()
            label = cls.LABELS[key]
            lines = cls.lines(text)
            if required and not text:
                errors.append(f'{label} is required.')
            elif len(text) > limit:
                errors.append(f'{label} must not be longer than {limit} characters.')
            elif len(lines) > max_lines:
                errors.append(f'{label} may have at most {max_lines} line(s).')
            elif max_lines > 1 and any(len(x) > cls.LINE_MAX for x in lines):
                errors.append(f'Each line of {label} must not be longer than {cls.LINE_MAX} characters.')
            data[key] = '\n'.join(lines) if max_lines > 1 else ' '.join(text.split())
        return data, errors

    @staticmethod
    def save_values(data, user_id):
        for key, value in data.items():
            execute("INSERT INTO landing_content (content_key, content_value, updated_by) VALUES (%s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE content_value = VALUES(content_value), updated_by = VALUES(updated_by)",
                    (key, value, user_id))

    @staticmethod
    def restore_defaults(section, user_id=None):
        keys = [k for k, *_ in Landing.SECTIONS[section]]
        execute('DELETE FROM landing_content WHERE content_key IN (%s)' % ','.join(['%s'] * len(keys)), keys)

    # ---------- banner ----------
    @classmethod
    def _folder(cls):
        return os.path.join(current_app.static_folder, 'img')

    @classmethod
    def save_banner(cls, file, user_id):
        """Ibinabalik ang mensahe ng error, o None kung ok."""
        if file is None or not file.filename:
            return 'Choose an image first.'
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in cls.IMAGE_TYPES:
            return 'The banner must be a JPG, PNG or WEBP image.'
        blob = file.read(cls.IMAGE_MAX + 1)
        if len(blob) > cls.IMAGE_MAX:
            return 'The image is too large. The limit is 3 MB.'
        if not blob.startswith(cls.IMAGE_TYPES[ext]) or (ext == '.webp' and blob[8:12] != b'WEBP'):
            return 'That file is not a valid image.'
        name = f"banner_{datetime.now():%Y%m%d%H%M%S}{ext}"
        os.makedirs(cls._folder(), exist_ok=True)
        with open(os.path.join(cls._folder(), name), 'wb') as handle:
            handle.write(blob)
        cls.reset_banner(user_id, keep=name)
        cls.save_values({'hero_image': name}, user_id)
        return None

    @classmethod
    def reset_banner(cls, user_id, keep=None):
        """Binubura ang lumang na-upload na banner (hindi ang hero.jpg) at ibinabalik ang default."""
        row = query("SELECT content_value FROM landing_content WHERE content_key = 'hero_image'", one=True)
        old = row['content_value'] if row else ''
        if old and old != keep and re.fullmatch(r'banner_\d{14}\.(jpg|jpeg|png|webp)', old):
            try:
                os.remove(os.path.join(cls._folder(), old))
            except OSError:
                pass
        if keep is None:
            execute("DELETE FROM landing_content WHERE content_key = 'hero_image'")

    # ---------- contact info (settings table) ----------
    CONTACT = (('school_address', 'Address', 200), ('school_email', 'School email', 120),
               ('school_phone', 'Phone', 40), ('helpdesk_email', 'HelpDesk email', 120))

    @classmethod
    def clean_contact(cls, form):
        data, errors = {}, []
        for key, label, limit in cls.CONTACT:
            value = ' '.join(form.get(key, '').split())
            if not value:
                errors.append(f'{label} is required.')
            elif len(value) > limit:
                errors.append(f'{label} must not be longer than {limit} characters.')
            elif key.endswith('email') and not EMAIL_RE.match(value):
                errors.append(f'{label} is not a valid email address.')
            data[key] = value
        return data, errors

    @staticmethod
    def save_contact(data):
        for key, value in data.items():
            execute("INSERT INTO settings (setting_key, setting_value) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)", (key, value))

    # ---------- programs ----------
    @staticmethod
    def programs():
        return query('SELECT * FROM programs ORDER BY id')

    @staticmethod
    def program(program_id):
        return query('SELECT * FROM programs WHERE id = %s', (program_id,), one=True)

    @staticmethod
    def clean_program(form):
        data, errors = {}, []
        name = ' '.join(form.get('name', '').split())
        if not 3 <= len(name) <= 120:
            errors.append('The program name must be 3 to 120 characters.')
        data['name'] = name
        for key, label in (('objective', 'Objective'), ('prerequisites', 'Prerequisite')):
            text = form.get(key, '').strip()
            if len(text) > 1000:
                errors.append(f'{label} must not be longer than 1000 characters.')
            data[key] = text or None
        data['is_active'] = 1 if form.get('is_active') == '1' else 0
        return data, errors

    @staticmethod
    def save_program(program_id, data):
        execute('UPDATE programs SET name = %s, objective = %s, prerequisites = %s, is_active = %s WHERE id = %s',
                (data['name'], data['objective'], data['prerequisites'], data['is_active'], program_id))