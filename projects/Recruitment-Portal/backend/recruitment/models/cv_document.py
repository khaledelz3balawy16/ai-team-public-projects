import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .base import ValidatedModel


def generated_cv_storage_key():
    return f"cvs/{uuid.uuid4()}"


class CVDocument(ValidatedModel):
    class ScanStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CLEAN = "CLEAN", "Clean"
        REJECTED = "REJECTED", "Rejected"
        FAILED = "FAILED", "Failed"

    application = models.OneToOneField("recruitment.Application", on_delete=models.CASCADE, related_name="cv_document")
    storage_key = models.CharField(max_length=200, unique=True, default=generated_cv_storage_key, editable=False)
    original_filename = models.CharField(max_length=255)
    file_extension = models.CharField(max_length=8)
    content_type = models.CharField(max_length=120)
    size_bytes = models.PositiveBigIntegerField()
    sha256_checksum = models.CharField(max_length=64, blank=True)
    security_scan_status = models.CharField(max_length=12, choices=ScanStatus, default=ScanStatus.PENDING)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(size_bytes__gt=0, size_bytes__lte=10 * 1024 * 1024), name="cv_size_in_bounds"),
            models.CheckConstraint(condition=models.Q(file_extension__in=["pdf", "doc", "docx"]), name="cv_allowed_extension"),
            models.CheckConstraint(condition=models.Q(security_scan_status__in=["PENDING", "CLEAN", "REJECTED", "FAILED"]), name="cv_valid_scan_status"),
        ]

    def clean(self):
        super().clean()
        if not re.fullmatch(r"cvs/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", self.storage_key or ""):
            raise ValidationError({"storage_key": "Use a generated UUID storage key."})
        if self.file_extension not in settings.CV_ALLOWED_EXTENSIONS:
            raise ValidationError({"file_extension": "Only PDF, DOC and DOCX are permitted."})
        if self.size_bytes is None or not 0 < self.size_bytes <= settings.CV_MAX_SIZE_BYTES:
            raise ValidationError({"size_bytes": "CV size must be positive and at most 10 MiB."})
        mime_types = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        if self.content_type != mime_types.get(self.file_extension):
            raise ValidationError({"content_type": "MIME type must match the declared extension; content scanning is still required."})
        if not self.original_filename or any(c in self.original_filename for c in ("/", "\\", "\x00", "\r", "\n")):
            raise ValidationError({"original_filename": "Store only a filename, without paths or control characters."})
        if self.sha256_checksum and not re.fullmatch(r"[0-9a-f]{64}", self.sha256_checksum):
            raise ValidationError({"sha256_checksum": "Use a lowercase hexadecimal SHA-256 digest."})
