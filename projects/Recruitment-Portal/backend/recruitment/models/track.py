from django.db import models

from .base import TimestampedModel


class Track(TimestampedModel):
    event = models.ForeignKey("recruitment.Event", on_delete=models.PROTECT, related_name="tracks")
    name = models.CharField(max_length=150)
    code = models.SlugField(max_length=80)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "code"]
        constraints = [models.UniqueConstraint(fields=["event", "code"], name="unique_event_track_code")]
        indexes = [models.Index(fields=["event", "is_active", "display_order"], name="track_event_display_idx")]

    def clean(self):
        super().clean()
        if not self._state.adding:
            from django.core.exceptions import ValidationError
            old = type(self).objects.get(pk=self.pk)
            if old.event_id != self.event_id and self.applications.exists():
                raise ValidationError({"event": "Cannot move a track with applications to another event."})

    def __str__(self):
        return self.name
