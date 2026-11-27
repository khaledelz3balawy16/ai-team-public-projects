from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from .base import TimestampedModel


class Event(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        CLOSED = "CLOSED", "Closed"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=160, unique=True)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    applications_open_at = models.DateTimeField(null=True, blank=True)
    applications_close_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status, default=Status.DRAFT)
    privacy_notice_url = models.URLField(max_length=500, blank=True)
    privacy_notice_version = models.CharField(max_length=80, blank=True)
    retention_days = models.PositiveIntegerField(default=365)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(status__in=["DRAFT", "PUBLISHED", "CLOSED"]), name="event_valid_status"),
            models.CheckConstraint(condition=Q(ends_at__isnull=True) | Q(starts_at__isnull=True) | Q(ends_at__gte=F("starts_at")), name="event_dates_ordered"),
            models.CheckConstraint(condition=Q(applications_close_at__isnull=True) | Q(applications_open_at__isnull=True) | Q(applications_close_at__gte=F("applications_open_at")), name="event_window_ordered"),
            models.CheckConstraint(condition=Q(retention_days__gt=0), name="event_retention_positive"),
            models.CheckConstraint(condition=~Q(status="PUBLISHED") | (~Q(privacy_notice_url="") & ~Q(privacy_notice_version="")), name="published_event_privacy"),
        ]

    def clean(self):
        super().clean()
        for start, end in (("starts_at", "ends_at"), ("applications_open_at", "applications_close_at")):
            if getattr(self, start) and getattr(self, end) and getattr(self, end) < getattr(self, start):
                raise ValidationError({end: "Closing date must not precede opening date."})
        if self.status == self.Status.PUBLISHED and (
            not self.privacy_notice_url.strip() or not self.privacy_notice_version.strip()
            or not self.privacy_notice_url.startswith("https://")
        ):
            raise ValidationError("Published events require an HTTPS privacy notice and a version.")

    def __str__(self):
        return self.title
