from pathlib import Path
from uuid import uuid4

from django.utils.deconstruct import deconstructible


@deconstructible
class UploadTo:
    """Fayl nomini tasodifiy uuid bilan almashtiradi: covers/3f2a...c1.jpg.

    Nomlarni taxmin qilib bo'lmaydi, shuning uchun hali ochilmagan sahifalar
    havolasini topib bo'lmaydi.
    """

    def __init__(self, folder: str):
        self.folder = folder

    def __call__(self, instance, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        return f"{self.folder}/{uuid4().hex}{ext}"

    def __eq__(self, other):
        return isinstance(other, UploadTo) and other.folder == self.folder
