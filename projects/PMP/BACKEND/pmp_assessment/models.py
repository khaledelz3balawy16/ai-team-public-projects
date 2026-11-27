from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

PERFORMANCE_DOMAINS = ["Governance", "Scope", "Schedule", "Finance", "Stakeholders", "Resources", "Risk"]
PERFORMANCE_DOMAIN_CHOICES = [(x, x) for x in PERFORMANCE_DOMAINS]
DOMAIN_EXAM_QUESTION_COUNT = 40
PERFORMANCE_DOMAIN_TARGET = DOMAIN_EXAM_QUESTION_COUNT
QUESTION_TYPES = [
    ("Single Response", "Single Response"),
    ("Multiple Response", "Multiple Response"),
    ("Case Study", "Case Study"),
    ("Graphic", "Graphic"),
    ("Case Study Graphic", "Case Study Graphic"),
]
IMPORT_STATUSES = [("ready", "Ready"), ("needs_domain_mapping", "Needs Domain Mapping")]
USER_TYPES = [("KBC_LEARNER", "KBC Learner"), ("EXTERNAL", "External Candidate")]
PROFILE_STATUSES = [("active", "Active"), ("unresolved", "Unresolved"), ("disabled", "Disabled")]
TOKEN_PURPOSES = [("email_verification", "Email Verification"), ("password_reset", "Password Reset")]

def normalize_email(value):
    return str(value or "").strip().lower()

class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class KBCPmpLearnerRegistry(TimestampedModel):
    source_learner_id = models.CharField(max_length=120, blank=True, unique=True, null=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    normalized_email = models.EmailField(unique=True, db_index=True)
    programme = models.CharField(max_length=255, blank=True)
    cohort = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50, default="active")
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        indexes = [models.Index(fields=["normalized_email"]), models.Index(fields=["programme"]), models.Index(fields=["status"])]
    def save(self, *args, **kwargs):
        self.normalized_email = normalize_email(self.email)
        super().save(*args, **kwargs)
    def __str__(self): return f"{self.full_name} <{self.email}>"

class LearnerProfile(TimestampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="pmp_profile")
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default="EXTERNAL")
    kbc_registry = models.ForeignKey(KBCPmpLearnerRegistry, null=True, blank=True, on_delete=models.PROTECT, related_name="profiles")
    name = models.CharField(max_length=255)
    email = models.EmailField()
    normalized_email = models.EmailField(unique=True, null=True, blank=True, db_index=True)
    job_title = models.CharField(max_length=255, blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    industry = models.CharField(max_length=255, blank=True)
    role_description = models.TextField(blank=True)
    experience_level = models.CharField(max_length=100, blank=True)
    years_project_experience = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_kbc_learner = models.BooleanField(default=False)
    programme = models.CharField(max_length=255, blank=True)
    cohort = models.CharField(max_length=255, blank=True)
    linkedin_url = models.URLField(blank=True)
    profile_completed = models.BooleanField(default=False)
    apprenticeship_interest = models.BooleanField(default=False)
    marketing_consent = models.BooleanField(default=False)
    marketing_consent_at = models.DateTimeField(null=True, blank=True)
    marketing_opted_out_at = models.DateTimeField(null=True, blank=True)
    preferred_contact = models.CharField(max_length=30, blank=True)
    email_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=PROFILE_STATUSES, default="active")
    future_lms_user_id = models.CharField(max_length=120, blank=True, null=True)
    future_lms_learner_id = models.CharField(max_length=120, blank=True, null=True)
    lms_linked_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        indexes = [models.Index(fields=["normalized_email"]), models.Index(fields=["user_type"]), models.Index(fields=["status"])]
    def save(self, *args, **kwargs):
        self.normalized_email = normalize_email(self.email)
        self.is_kbc_learner = self.user_type == "KBC_LEARNER"
        super().save(*args, **kwargs)
    def __str__(self): return f"{self.name} <{self.email}>"

class PMPAuthToken(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pmp_auth_tokens")
    purpose = models.CharField(max_length=30, choices=TOKEN_PURPOSES)
    token_hash = models.CharField(max_length=64, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        indexes = [models.Index(fields=["purpose", "token_hash"]), models.Index(fields=["expires_at"])]
    @property
    def is_usable(self): return self.used_at is None and self.expires_at > timezone.now()

class PMPDomain(TimestampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    def __str__(self): return self.name

class PMPTopic(TimestampedModel):
    domain = models.ForeignKey(PMPDomain, on_delete=models.PROTECT, related_name="topics")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["domain", "name"], name="unique_pmp_topic_per_domain")]
    def __str__(self): return f"{self.domain}: {self.name}"

class PMPQuestion(TimestampedModel):
    METHODOLOGIES = [(x, x) for x in ["Agile", "Hybrid", "Predictive", "Waterfall", "General"]]
    DIFFICULTIES = [(x, x) for x in ["Easy", "Medium", "Hard"]]
    question_id = models.CharField(max_length=100, blank=True, db_index=True)
    performance_domain = models.CharField(max_length=30, choices=PERFORMANCE_DOMAIN_CHOICES, blank=False, default="", db_index=True)
    eco_domain = models.CharField(max_length=100, blank=True)
    eco_task = models.CharField(max_length=255, blank=True)
    question_type = models.CharField(max_length=40, choices=QUESTION_TYPES, default="Single Response")
    question_text = models.TextField()
    domain = models.ForeignKey(PMPDomain, on_delete=models.PROTECT, related_name="questions")
    topic = models.ForeignKey(PMPTopic, null=True, blank=True, on_delete=models.PROTECT, related_name="questions")
    task = models.CharField(max_length=255, blank=True)
    methodology = models.CharField(max_length=20, choices=METHODOLOGIES, default="General")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTIES, default="Medium")
    correct_answer_explanation = models.TextField(blank=True)
    wrong_answer_explanation = models.TextField(blank=True)
    pmp_reference = models.CharField(max_length=255, blank=True)
    chapter_reference = models.CharField(max_length=255, blank=True)
    source_file = models.CharField(max_length=255, blank=True)
    source_sheet = models.CharField(max_length=255, blank=True)
    source_year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    source_item_id = models.CharField(max_length=120, blank=True)
    case_group_id = models.CharField(max_length=120, blank=True, db_index=True)
    case_text = models.TextField(blank=True)
    exhibit_blob_name = models.CharField(max_length=255, blank=True, db_index=True)
    exhibit_alt_text = models.CharField(max_length=255, blank=True)
    is_synthetic = models.BooleanField(default=False, db_index=True)
    duplicate_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicate_questions")
    import_status = models.CharField(max_length=30, choices=IMPORT_STATUSES, default="ready", db_index=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        indexes = [
            models.Index(fields=["domain"]), models.Index(fields=["topic"]), models.Index(fields=["is_active"]),
            models.Index(fields=["performance_domain"]), models.Index(fields=["eco_domain"]), models.Index(fields=["question_type"]),
            models.Index(fields=["source_file", "source_sheet"]),
        ]
    def clean(self):
        if self.performance_domain and self.performance_domain not in PERFORMANCE_DOMAINS:
            raise ValidationError({"performance_domain": "Unsupported PMP performance domain."})
        if self.topic_id and self.domain_id and self.topic.domain_id != self.domain_id:
            raise ValidationError({"topic": "Topic must belong to the selected domain."})
        if self.performance_domain:
            self.import_status = "ready"
    def __str__(self): return self.question_text[:80]

class PMPQuestionOption(TimestampedModel):
    question = models.ForeignKey(PMPQuestion, on_delete=models.CASCADE, related_name="options")
    option_label = models.CharField(max_length=5)
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["question", "option_label"], name="unique_option_label_per_question")]
        ordering = ["option_label"]
    def __str__(self): return f"{self.option_label}. {self.option_text[:50]}"

class PMPExhibit(TimestampedModel):
    EXHIBIT_TYPES = [(x, x.replace("_", " ").title()) for x in ["image", "chart", "table", "diagram", "text", "case_study"]]
    STORAGE_BACKENDS = [(x, x.title()) for x in ["local", "azure", "external", "none"]]
    title = models.CharField(max_length=255, db_index=True)
    exhibit_type = models.CharField(max_length=30, choices=EXHIBIT_TYPES)
    storage_backend = models.CharField(max_length=20, choices=STORAGE_BACKENDS, default="none")
    storage_path = models.CharField(max_length=500, blank=True)
    external_url = models.URLField(blank=True)
    content = models.TextField(blank=True)
    caption = models.TextField(blank=True)
    source_exam = models.CharField(max_length=100, blank=True, db_index=True)
    source_question_number = models.PositiveSmallIntegerField(null=True, blank=True)
    source_label = models.CharField(max_length=255, blank=True, db_index=True)
    checksum = models.CharField(max_length=64, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    questions = models.ManyToManyField(PMPQuestion, through="PMPQuestionExhibit", related_name="exhibits")
    class Meta:
        indexes = [models.Index(fields=["source_exam", "source_label"]), models.Index(fields=["exhibit_type"])]
        constraints = [models.UniqueConstraint(fields=["source_exam", "source_label", "checksum"], name="unique_exhibit_source_label_checksum")]
    def __str__(self): return self.title

class PMPQuestionExhibit(models.Model):
    question = models.ForeignKey(PMPQuestion, on_delete=models.CASCADE)
    exhibit = models.ForeignKey(PMPExhibit, on_delete=models.CASCADE)
    display_order = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["question", "exhibit"], name="unique_question_exhibit_link"),
        ]
    def __str__(self): return f"{self.question_id} -> {self.exhibit_id}"

class PMPExamAttempt(TimestampedModel):
    EXAM_MODES = [("domain", "Domain"), ("quick", "Quick Practice"), ("random", "Random"), ("topic", "Topic"), ("exam_simulator", "PMP exam simulator"), ("full_practice", "Full question practice"),
                  ("practice_1", "Practice exam 1"), ("practice_2", "Practice exam 2"), ("practice_3", "Practice exam 3"), ("practice_4", "Practice exam 4"), ("practice_5", "Practice exam 5"),
                  ("methodology", "Methodology drill"), ("difficulty", "Difficulty drill")]
    STATUSES = [(x, x.replace("_", " ").title()) for x in ["created", "in_progress", "submitted", "report_generated", "failed", "expired", "abandoned"]]
    learner_profile = models.ForeignKey(LearnerProfile, on_delete=models.PROTECT, related_name="attempts")
    exam_mode = models.CharField(max_length=20, choices=EXAM_MODES)
    selected_domain = models.ForeignKey(PMPDomain, null=True, blank=True, on_delete=models.PROTECT)
    selected_topic = models.ForeignKey(PMPTopic, null=True, blank=True, on_delete=models.PROTECT)
    selected_methodology = models.CharField(max_length=20, blank=True)
    selected_difficulty = models.CharField(max_length=10, blank=True)
    question_count = models.PositiveSmallIntegerField()
    duration_minutes = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    current_question_index = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUSES, default="created")
    score_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    correct_count = models.PositiveSmallIntegerField(default=0)
    incorrect_count = models.PositiveSmallIntegerField(default=0)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    class Meta:
        indexes = [models.Index(fields=["learner_profile"]), models.Index(fields=["status"]), models.Index(fields=["last_activity_at"])]

class PMPExamAttemptQuestion(models.Model):
    attempt = models.ForeignKey(PMPExamAttempt, on_delete=models.CASCADE, related_name="attempt_questions")
    question = models.ForeignKey(PMPQuestion, on_delete=models.PROTECT)
    order_number = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["order_number"]
        constraints = [models.UniqueConstraint(fields=["attempt", "question"], name="unique_question_per_attempt"), models.UniqueConstraint(fields=["attempt", "order_number"], name="unique_attempt_order")]

class PMPExamAnswer(TimestampedModel):
    attempt = models.ForeignKey(PMPExamAttempt, on_delete=models.CASCADE, related_name="answers")
    attempt_question = models.ForeignKey(PMPExamAttemptQuestion, null=True, blank=True, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(PMPQuestion, on_delete=models.PROTECT)
    selected_option = models.ForeignKey(PMPQuestionOption, null=True, blank=True, on_delete=models.PROTECT)
    selected_options = models.ManyToManyField(PMPQuestionOption, blank=True, related_name="multi_response_answers")
    is_correct = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    answered_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "question"], name="unique_answer_per_attempt_question")]

class PMPAIReport(TimestampedModel):
    attempt = models.OneToOneField(PMPExamAttempt, on_delete=models.CASCADE, related_name="ai_report")
    report_json = models.JSONField()
    overall_summary = models.TextField(blank=True)
    performance_level = models.CharField(max_length=50, blank=True)
    generated_at = models.DateTimeField()
