from django.db import models
from django.db.models.functions import Lower, Trim

from .base import TimestampedModel


class Applicant(TimestampedModel):
    class EducationStatus(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        FRESH_GRADUATE = "FRESH_GRADUATE", "Fresh graduate"
        GRADUATE = "GRADUATE", "Graduate"

    full_name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254)
    mobile_number = models.CharField(max_length=40)
    university = models.CharField(max_length=200)
    faculty_or_major = models.CharField(max_length=200)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    education_status = models.CharField(max_length=20, choices=EducationStatus)
    city = models.CharField(max_length=120)
    linkedin_url = models.URLField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower(Trim("email")), name="unique_applicant_normalized_email"),
            models.CheckConstraint(condition=models.Q(education_status__in=["STUDENT", "FRESH_GRADUATE", "GRADUATE"]), name="applicant_valid_education"),
        ]

    def clean_fields(self, exclude=None):
        # Normalize before EmailField validation, including surrounding whitespace.
        if isinstance(self.email, str):
            self.email = self.email.strip().lower()
        super().clean_fields(exclude=exclude)

    def __str__(self):
        # Avoid accidental identity data in generic object logs and history labels.
        return f"Applicant {self.pk}"
