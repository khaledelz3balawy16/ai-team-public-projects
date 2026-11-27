import uuid

from django.db import models


class ValidatedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Ordinary ORM writes and Admin validate. Bulk/update/raw writes bypass this:
        # Phase 2 services must validate and lock cross-row invariants explicitly.
        self.full_clean()
        return super().save(*args, **kwargs)


class TimestampedModel(ValidatedModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
