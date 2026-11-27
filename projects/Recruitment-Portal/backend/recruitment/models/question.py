import math

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.db.models import F, Q

from .base import TimestampedModel, ValidatedModel


def is_finite_number(value):
    # bool is an int subclass but is never a numeric JSON answer. Avoid float
    # coercion of large integers, which can raise OverflowError.
    return type(value) is int or (type(value) is float and math.isfinite(value))


class Question(TimestampedModel):
    class Type(models.TextChoices):
        SHORT_TEXT = "SHORT_TEXT", "Short text"
        LONG_TEXT = "LONG_TEXT", "Long text"
        SINGLE_CHOICE = "SINGLE_CHOICE", "Single choice"
        MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Multiple choice"
        YES_NO = "YES_NO", "Yes / No"
        NUMBER = "NUMBER", "Number"
        URL = "URL", "URL"

    track = models.ForeignKey("recruitment.Track", on_delete=models.CASCADE, related_name="questions")
    key = models.SlugField(max_length=80)
    title = models.TextField()
    description = models.TextField(blank=True)
    question_type = models.CharField(max_length=20, choices=Type)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    placeholder = models.CharField(max_length=250, blank=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["display_order", "key"]
        constraints = [
            models.UniqueConstraint(fields=["track", "key"], name="unique_track_question_key"),
            models.CheckConstraint(condition=Q(question_type__in=["SHORT_TEXT", "LONG_TEXT", "SINGLE_CHOICE", "MULTIPLE_CHOICE", "YES_NO", "NUMBER", "URL"]), name="question_valid_type"),
        ]
        indexes = [models.Index(fields=["track", "is_active", "display_order"], name="question_track_display_idx")]

    def clean(self):
        super().clean()
        allowed = {
            self.Type.SHORT_TEXT: {"min_length", "max_length"},
            self.Type.LONG_TEXT: {"min_length", "max_length"},
            self.Type.NUMBER: {"min_value", "max_value"},
            self.Type.MULTIPLE_CHOICE: {"min_selections", "max_selections"},
        }.get(self.question_type, set())
        if not isinstance(self.settings, dict) or set(self.settings) - allowed:
            raise ValidationError({"settings": "Use only supported metadata keys for this question type."})
        for key, value in self.settings.items():
            if not is_finite_number(value):
                raise ValidationError({"settings": "Metadata bounds must be finite numbers."})
            if key not in ("min_value", "max_value") and (type(value) is not int or value < 0):
                raise ValidationError({"settings": "Length and selection bounds must be non-negative integers."})
        for low, high in (("min_length", "max_length"), ("min_value", "max_value"), ("min_selections", "max_selections")):
            if low in self.settings and high in self.settings and self.settings[low] > self.settings[high]:
                raise ValidationError({"settings": "Minimum cannot exceed maximum."})
        if not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            if self.answers.exists() and (old.track_id != self.track_id or old.question_type != self.question_type or old.key != self.key):
                raise ValidationError("Answered questions cannot change track, type or stable key; create a new question.")
            if self.options.exists() and self.question_type not in (self.Type.SINGLE_CHOICE, self.Type.MULTIPLE_CHOICE):
                raise ValidationError("A question with options must remain a choice question.")
            # Validate both sides when an administrator reorders/moves a question.
            for condition in QuestionCondition.objects.filter(Q(source_question=self) | Q(target_question=self)):
                if condition.source_question_id == self.pk:
                    condition.source_question = self
                if condition.target_question_id == self.pk:
                    condition.target_question = self
                condition.clean()

    def __str__(self):
        return self.key


def validate_response(question, value, *, active_options=True):
    """Typed JSON contract shared by answers and condition expected values."""
    kind = question.question_type
    if kind in (Question.Type.SHORT_TEXT, Question.Type.LONG_TEXT, Question.Type.URL):
        valid = isinstance(value, str) and bool(value.strip())
        if valid and kind == Question.Type.URL:
            URLValidator(schemes=["http", "https"])(value)
    elif kind == Question.Type.YES_NO:
        valid = type(value) is bool
    elif kind == Question.Type.NUMBER:
        valid = is_finite_number(value)
    elif kind in (Question.Type.SINGLE_CHOICE, Question.Type.MULTIPLE_CHOICE):
        choices = question.options.all()
        if active_options:
            choices = choices.filter(is_active=True)
        allowed = set(choices.values_list("value", flat=True))
        if kind == Question.Type.SINGLE_CHOICE:
            valid = isinstance(value, str) and value in allowed
        else:
            valid = (
                isinstance(value, list) and bool(value)
                and all(isinstance(v, str) and v in allowed for v in value)
                and len(value) == len(set(value))
            )
    else:
        valid = False
    if not valid:
        raise ValidationError("Response must be non-empty typed JSON using permitted option values.")
    metadata = question.settings
    bound_value = len(value) if isinstance(value, (str, list)) else value
    low, high = (
        ("min_selections", "max_selections") if kind == Question.Type.MULTIPLE_CHOICE
        else ("min_length", "max_length") if kind in (Question.Type.SHORT_TEXT, Question.Type.LONG_TEXT)
        else ("min_value", "max_value") if kind == Question.Type.NUMBER
        else (None, None)
    )
    if (low in metadata and bound_value < metadata[low]) or (high in metadata and bound_value > metadata[high]):
        raise ValidationError("Response falls outside configured bounds.")


class QuestionOption(TimestampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    value = models.SlugField(max_length=100)
    label = models.CharField(max_length=200)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "value"]
        constraints = [models.UniqueConstraint(fields=["question", "value"], name="unique_question_option_value")]

    def clean(self):
        super().clean()
        if self.question_id and self.question.question_type not in (Question.Type.SINGLE_CHOICE, Question.Type.MULTIPLE_CHOICE):
            raise ValidationError({"question": "Only choice questions support options."})
        if not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            if (old.value, old.question_id) != (self.value, self.question_id):
                raise ValidationError("Option values and owning questions are stable; change the label or deactivate instead.")

    def __str__(self):
        return self.label


class QuestionCondition(ValidatedModel):
    class Operator(models.TextChoices):
        EQUALS = "EQUALS", "Equals"
        NOT_EQUALS = "NOT_EQUALS", "Does not equal"
        CONTAINS = "CONTAINS", "Contains"

    target_question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="conditions")
    source_question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="dependent_conditions")
    operator = models.CharField(max_length=16, choices=Operator)
    expected_value = models.JSONField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(source_question=F("target_question")), name="condition_not_self"),
            models.CheckConstraint(condition=Q(operator__in=["EQUALS", "NOT_EQUALS", "CONTAINS"]), name="condition_valid_operator"),
        ]

    def clean(self):
        super().clean()
        if not self.source_question_id or not self.target_question_id:
            return
        source, target = self.source_question, self.target_question
        if source.pk == target.pk:
            raise ValidationError("A question cannot depend on itself.")
        if source.track_id != target.track_id:
            raise ValidationError("Condition questions must belong to the same track.")
        if source.display_order >= target.display_order:
            raise ValidationError("The source must have a strictly smaller display order.")
        # Explicit graph check also detects a cycle if existing data was bulk-written.
        pending, visited = [target.pk], set()
        edges = list(type(self).objects.exclude(pk=self.pk).values_list("source_question_id", "target_question_id"))
        while pending:
            current = pending.pop()
            if current == source.pk:
                raise ValidationError("Circular question conditions are forbidden.")
            if current not in visited:
                visited.add(current)
                pending.extend(end for start, end in edges if start == current)
        try:
            if self.operator == self.Operator.CONTAINS:
                if source.question_type == Question.Type.MULTIPLE_CHOICE:
                    if not isinstance(self.expected_value, str) or not source.options.filter(value=self.expected_value, is_active=True).exists():
                        raise ValidationError("CONTAINS expects one active stable option value.")
                elif source.question_type in (Question.Type.SHORT_TEXT, Question.Type.LONG_TEXT):
                    if not isinstance(self.expected_value, str) or not self.expected_value.strip():
                        raise ValidationError("CONTAINS expects a non-empty substring.")
                else:
                    raise ValidationError("CONTAINS requires a text or multiple-choice source.")
            elif self.operator in (self.Operator.EQUALS, self.Operator.NOT_EQUALS):
                validate_response(source, self.expected_value)
            else:
                raise ValidationError("Unknown condition operator.")
        except ValidationError as error:
            raise ValidationError({"expected_value": error.messages}) from error
