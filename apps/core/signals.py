from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import CleanupFilesMixin, delete_file_on_commit


@receiver(post_delete)
def delete_files_after_delete(sender, instance, **kwargs):
    if not isinstance(instance, CleanupFilesMixin):
        return
    for field_name in instance.cleanup_file_fields:
        file = getattr(instance, field_name)
        if file and file.name:
            delete_file_on_commit(file.storage, file.name)
