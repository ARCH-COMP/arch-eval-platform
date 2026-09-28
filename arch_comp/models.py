from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone


secret_dataset_storage = FileSystemStorage(location=settings.DATA_DIR)


def current_season() -> str:
    return str(timezone.now().year)


class SecretDataset(models.Model):
    category = models.CharField(max_length=32)
    season = models.CharField(max_length=16)
    archive = models.FileField(storage=secret_dataset_storage, upload_to="secret-data/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey("core.User", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = (("category", "season"),)
        ordering = ["-uploaded_at", "category", "season"]

    def __str__(self) -> str:
        return f"{self.category} {self.season}"

    def delete(self, using=None, keep_parents=False):
        archive_name = self.archive.name
        storage = self.archive.storage
        super().delete(using=using, keep_parents=keep_parents)
        if archive_name:
            storage.delete(archive_name)
