from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .application import Application
from .base import ValidatedModel


class ApplicationStatusHistory(ValidatedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=16, choices=Application.Status, null=True, blank=True)
    new_status = models.CharField(max_length=16, choices=Application.Status)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="recruitment_status_changes")
    note = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(previous_status__isnull=True) | models.Q(previous_status__in=Application.Status.values), name="history_valid_previous"),
            models.CheckConstraint(condition=models.Q(new_status__in=Application.Status.values), name="history_valid_new"),
        ]
        indexes = [models.Index(fields=["application", "changed_at"], name="history_application_time_idx")]

    def clean(self):
        super().clean()
        if self.previous_status == self.new_status:
            raise ValidationError("A history entry must describe an actual status transition.")
        if not self._state.adding:
            raise ValidationError("Status history is append-only; entries cannot be edited.")
