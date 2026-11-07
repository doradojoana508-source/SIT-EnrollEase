import io
import os
import time
from flask import current_app
from PIL import Image, ImageOps
from db import execute


class Profile:
    """Profile ng sariling account: pangalan, larawan at pagpalit ng email."""

    MAX_BYTES = 5 * 1024 * 1024
    MAX_SIDE = 8000                       # pixels; iwas sobrang laking larawan
    SIZE = 256                            # parisukat na larawan na ito ang ise-save
    FORMATS = ('JPEG', 'PNG', 'WEBP')

    # ---- pangalan ----
    @staticmethod
    def update_name(user, first, middle, last):
        execute("UPDATE users SET first_name=%s, middle_name=%s, last_name=%s WHERE id=%s",
                (first, middle or None, last, user.id))

    # ---- larawan ----
    @staticmethod
    def folder():
        path = os.path.join(current_app.root_path, 'uploads', 'avatars')
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def photo_path(cls, user):
        """Ang file ng larawan ng user, o None kung wala."""
        if not user.photo:
            return None
        path = os.path.join(cls.folder(), os.path.basename(user.photo))
        return path if os.path.isfile(path) else None

    @classmethod
    def save_photo(cls, user, storage):
        """Sinusuri ang larawan, ginagawang 256x256 JPEG (natatanggal ang EXIF) at sine-save. Ibinabalik ang error text o None."""
        data = storage.read(cls.MAX_BYTES + 1)
        if not data:
            return 'Choose a photo first.'
        if len(data) > cls.MAX_BYTES:
            return 'The photo must be 5 MB or smaller.'
        try:
            image = Image.open(io.BytesIO(data))
            if image.format not in cls.FORMATS:
                return 'Use a JPG, PNG or WEBP photo.'
            if max(image.size) > cls.MAX_SIDE:
                return 'That photo is too large in pixels. Please use a smaller one.'
            image = ImageOps.exif_transpose(image).convert('RGB')
        except Exception:
            return 'That file is not a valid photo.'
        side = min(image.size)                                  # gitnang parisukat
        left, top = (image.width - side) // 2, (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side)).resize((cls.SIZE, cls.SIZE), Image.LANCZOS)
        name = f'{user.id}_{int(time.time())}.jpg'
        image.save(os.path.join(cls.folder(), name), 'JPEG', quality=85, optimize=True)
        old = cls.photo_path(user)
        execute("UPDATE users SET photo=%s WHERE id=%s", (name, user.id))
        user.photo = name
        if old:
            try:
                os.remove(old)
            except OSError:
                pass
        return None

    @classmethod
    def remove_photo(cls, user):
        old = cls.photo_path(user)
        execute("UPDATE users SET photo=NULL WHERE id=%s", (user.id,))
        user.photo = None
        if old:
            try:
                os.remove(old)
            except OSError:
                pass

    