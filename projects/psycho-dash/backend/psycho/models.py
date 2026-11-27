from django.db import models


class AssessmentScore(models.Model):
    """
    Mirror of wp_assessment_scores — all JSON columns stored as JSONField.
    The 'email' field is the primary lookup key (same as WP).
    """
    email = models.EmailField(unique=True, db_index=True)

    # Psychological assessments
    wellbeing_score     = models.JSONField(null=True, blank=True)
    psychological_score = models.JSONField(null=True, blank=True)
    personality_score   = models.JSONField(null=True, blank=True)
    career_score        = models.JSONField(null=True, blank=True)
    riasec_score        = models.JSONField(null=True, blank=True)
    ei_score            = models.JSONField(null=True, blank=True)
    work_score          = models.JSONField(null=True, blank=True)
    cognitive_score     = models.JSONField(null=True, blank=True)   # CognitiveSkills_score
    logical_score       = models.JSONField(null=True, blank=True)   # LogicalSkills_score
    knowledge_score     = models.JSONField(null=True, blank=True)
    skills_score        = models.JSONField(null=True, blank=True)
    behaviors_score     = models.JSONField(null=True, blank=True)
    learning_style_score = models.JSONField(null=True, blank=True)

    # Career path (AI-generated, saved after generation)
    career_recommendations = models.JSONField(null=True, blank=True)
    skills_to_develop      = models.JSONField(null=True, blank=True)
    career_path_last_shown = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assessment_scores'

    def __str__(self):
        return self.email

    def count_completed(self):
        """Returns how many of the 12 core assessments have data."""
        fields = [
            'wellbeing_score', 'psychological_score', 'personality_score',
            'career_score', 'riasec_score', 'ei_score', 'work_score',
            'cognitive_score', 'logical_score', 'knowledge_score',
            'skills_score', 'behaviors_score',
        ]
        return sum(1 for f in fields if getattr(self, f))

    def to_assessment_data(self):
        """Returns the ASSESSMENT_DATA dict shape the frontend expects."""
        return {
            'wellbeing':      self.wellbeing_score or {},
            'psychological':  self.psychological_score or {},
            'personality':    self.personality_score or {},
            'career':         self.career_score or {},
            'riasec':         self.riasec_score or {},
            'ei':             self.ei_score or {},
            'work':           self.work_score or {},
            'cognitive':      self.cognitive_score or {},
            'logical':        self.logical_score or {},
            'knowledge':      self.knowledge_score or {},
            'skills':         self.skills_score or {},
            'behaviors':      self.behaviors_score or {},
            'learning_style': self.learning_style_score or {},
        }


class SelfAssessmentQuestion(models.Model):
    question_id = models.TextField()
    label = models.TextField(blank=True, null=True)
    assessment_type = models.TextField(db_index=True)
    question_text = models.TextField()
    options = models.JSONField(default=list)
    answer = models.TextField(blank=True, null=True)
    source_created_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'self_assessment_questions'
        ordering = ['assessment_type', 'label', 'question_id']
        constraints = [
            models.UniqueConstraint(
                fields=['assessment_type', 'question_id'],
                name='psycho_unique_assessment_type_question',
            )
        ]

    def __str__(self):
        return f'{self.assessment_type} / {self.question_id}'


class SelfAssessmentQuizResponse(models.Model):
    learner_id = models.BigIntegerField(blank=True, null=True, db_index=True)
    learner_name = models.TextField(blank=True, null=True)
    learner_email = models.TextField(blank=True, null=True, db_index=True)
    assessment_type = models.TextField(db_index=True)
    answers = models.JSONField(default=dict)
    scores = models.JSONField(default=dict)
    total_score = models.FloatField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'self_assessment_quiz_responses'
        ordering = ['-submitted_at', '-id']

    def __str__(self):
        return f'{self.assessment_type} / {self.learner_email or self.learner_id or self.id}'
