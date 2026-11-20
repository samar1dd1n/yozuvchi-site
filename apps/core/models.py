from django.db import models, transaction


def delete_file_on_commit(storage, name: str) -> None:
    """Faylni tranzaksiya muvaffaqiyatli tugagandan keyin o'chiradi."""
    if name:
        transaction.on_commit(lambda: storage.delete(name))


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    class Meta:
        abstract = True


class CleanupFilesMixin(models.Model):
    """Fayl almashtirilganda eski faylni diskdan o'chiradi.

    Obyekt o'chirilganda fayllarni core.signals o'chiradi (CASCADE holatida ham ishlaydi).
    """

    cleanup_file_fields: tuple[str, ...] = ()

    class Meta:
        abstract = True

    def _stored_file_names(self) -> dict[str, str]:
        if not self.pk or not self.cleanup_file_fields:
            return {}
        row = (
            type(self)._default_manager.filter(pk=self.pk)
            .values(*self.cleanup_file_fields)
            .first()
        )
        return row or {}

    def save(self, *args, **kwargs):
        previous = self._stored_file_names()
        super().save(*args, **kwargs)
        for field_name, old_name in previous.items():
            current = getattr(self, field_name)
            new_name = current.name if current else ""
            if old_name and old_name != new_name:
                storage = self._meta.get_field(field_name).storage
                delete_file_on_commit(storage, old_name)
