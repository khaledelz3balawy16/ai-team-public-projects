from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .base import TimestampedModel
from .question import validate_response


class Application(TimestampedModel):
    class OpportunityType(models.TextChoices):
        INTERNSHIP = "INTERNSHIP", "Internship"
        FULL_TIME = "FULL_TIME", "Full time"
        PART_TIME = "PART_TIME", "Part time"
        GRADUATE_PROGRAMME = "GRADUATE_PROGRAMME", "Graduate programme"
        OPEN_TO_ALL = "OPEN_TO_ALL", "Open to all"

    class ExperienceLevel(models.TextChoices):
        NO_EXPERIENCE = "NO_EXPERIENCE", "No experience"
        LESS_THAN_ONE_YEAR = "LESS_THAN_ONE_YEAR", "Less than one year"
        ONE_TO_TWO_YEARS = "ONE_TO_TWO_YEARS", "One to two years"
        THREE_TO_FIVE_YEARS = "THREE_TO_FIVE_YEARS", "Three to five years"
        MORE_THAN_FIVE_YEARS = "MORE_THAN_FIVE_YEARS", "More than five years"

    class WorkArrangement(models.TextChoices):
        ONSITE = "ONSITE", "Onsite"
        HYBRID = "HYBRID", "Hybrid"
        REMOTE = "REMOTE", "Remote"
        FLEXIBLE = "FLEXIBLE", "Flexible"

    class Availability(models.TextChoices):
        IMMEDIATELY = "IMMEDIATELY", "Immediately"
        WITHIN_ONE_MONTH = "WITHIN_ONE_MONTH", "Within one month"
        WITHIN_THREE_MONTHS = "WITHIN_THREE_MONTHS", "Within three months"
        FLEXIBLE = "FLEXIBLE", "Flexible"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        IN_REVIEW = "IN_REVIEW", "In review"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    event = models.ForeignKey("recruitment.Event", on_delete=models.PROTECT, related_name="applications")
    applicant = models.ForeignKey("recruitment.Applicant", on_delete=models.PROTECT, related_name="applications")
    track = models.ForeignKey("recruitment.Track", on_delete=models.PROTECT, related_name="applications")
    opportunity_type = models.CharField(max_length=24, choices=OpportunityType)
    experience_level = models.CharField(max_length=24, choices=ExperienceLevel)
    preferred_work_arrangement = models.CharField(max_length=16, choices=WorkArrangement)
    availability = models.CharField(max_length=24, choices=Availability)
    status = models.CharField(max_length=16, choices=Status, default=Status.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    privacy_notice_version = models.CharField(max_length=80, blank=True)
    privacy_acknowledged_at = models.DateTimeField(null=True, blank=True)
    external_cv_sharing_authorized_at = models.DateTimeField(null=True, blank=True)
    future_opportunities_opt_in = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "applicant"], name="unique_event_applicant"),
            models.CheckConstraint(condition=Q(status__in=["DRAFT", "SUBMITTED", "IN_REVIEW", "SHORTLISTED", "REJECTED", "WITHDRAWN"]), name="application_valid_status"),
            models.CheckConstraint(condition=~Q(status="DRAFT") | Q(submitted_at__isnull=True), name="draft_without_submission"),
            models.CheckConstraint(condition=Q(status__in=["DRAFT", "WITHDRAWN"]) | Q(submitted_at__isnull=False), name="submitted_status_timestamp"),
            models.CheckConstraint(condition=Q(submitted_at__isnull=True) | (Q(privacy_acknowledged_at__isnull=False) & ~Q(privacy_notice_version="")), name="submission_has_privacy"),
            models.CheckConstraint(condition=Q(opportunity_type__in=["INTERNSHIP", "FULL_TIME", "PART_TIME", "GRADUATE_PROGRAMME", "OPEN_TO_ALL"]), name="application_valid_opportunity"),
            models.CheckConstraint(condition=Q(experience_level__in=["NO_EXPERIENCE", "LESS_THAN_ONE_YEAR", "ONE_TO_TWO_YEARS", "THREE_TO_FIVE_YEARS", "MORE_THAN_FIVE_YEARS"]), name="application_valid_experience"),
            models.CheckConstraint(condition=Q(preferred_work_arrangement__in=["ONSITE", "HYBRID", "REMOTE", "FLEXIBLE"]), name="application_valid_arrangement"),
            models.CheckConstraint(condition=Q(availability__in=["IMMEDIATELY", "WITHIN_ONE_MONTH", "WITHIN_THREE_MONTHS", "FLEXIBLE"]), name="application_valid_availability"),
        ]
        indexes = [
            models.Index(fields=["event", "status"], name="application_event_status_idx"),
            models.Index(fields=["track", "status"], name="application_track_status_idx"),
            models.Index(fields=["status", "submitted_at"], name="application_status_time_idx"),
        ]

    def clean(self):
        super().clean()
        if self.track_id and self.event_id and self.track.event_id != self.event_id:
            raise ValidationError({"track": "Selected track must belong to the application event."})
        if self.submitted_at:
            if not self.privacy_acknowledged_at or not self.privacy_notice_version.strip():
                raise ValidationError("Submission requires a privacy acknowledgement and notice version.")
            if self.privacy_acknowledged_at > self.submitted_at:
                raise ValidationError("Privacy acknowledgement cannot follow submission.")
        if not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            if old.submitted_at and (
                old.track_id != self.track_id or old.event_id != self.event_id
                or old.applicant_id != self.applicant_id or old.submitted_at != self.submitted_at
                or old.privacy_notice_version != self.privacy_notice_version
                or old.privacy_acknowledged_at != self.privacy_acknowledged_at
            ):
                raise ValidationError("Submitted identity, track, event and acknowledgement are immutable; a controlled administrative workflow is required.")
            if self.answers.exclude(question__track_id=self.track_id).exists():
                raise ValidationError({"track": "Existing answers belong to a different track."})

    def __str__(self):
        return f"Application {self.pk}"


class ApplicationAnswer(TimestampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("recruitment.Question", on_delete=models.PROTECT, related_name="answers")
    response = models.JSONField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["application", "question"], name="unique_application_question")]

    def clean(self):
        super().clean()
        if self.application_id and self.question_id:
            if self.question.track_id != self.application.track_id:
                raise ValidationError({"question": "Question must belong to the application's track."})
            # Existing historical answers may refer to deactivated options. New/edited
            # responses must use active choices; deactivation does not rewrite history.
            unchanged = False
            if not self._state.adding:
                old = type(self).objects.get(pk=self.pk)
                unchanged = (old.response == self.response and old.question_id == self.question_id)
            try:
                validate_response(self.question, self.response, active_options=not unchanged)
            except ValidationError as error:
                raise ValidationError({"response": error.messages}) from error
