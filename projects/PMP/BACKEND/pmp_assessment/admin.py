from django.contrib import admin
from .models import *

class OptionInline(admin.TabularInline):
    model = PMPQuestionOption
    extra = 4

class QuestionExhibitInline(admin.TabularInline):
    model = PMPQuestionExhibit
    extra = 0
    autocomplete_fields = ["exhibit"]

class ExhibitQuestionInline(admin.TabularInline):
    model = PMPQuestionExhibit
    extra = 0
    autocomplete_fields = ["question"]

@admin.register(KBCPmpLearnerRegistry)
class KBCPmpLearnerRegistryAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "programme", "cohort", "status", "is_active", "last_synced_at"]
    list_filter = ["programme", "status", "is_active"]
    search_fields = ["full_name", "email", "source_learner_id"]

@admin.register(LearnerProfile)
class LearnerProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "user_type", "programme", "profile_completed", "email_verified", "attempt_count", "last_seen_at", "status"]
    list_filter = ["user_type", "programme", "status", "email_verified", "profile_completed"]
    search_fields = ["name", "email", "kbc_registry__source_learner_id", "future_lms_user_id", "future_lms_learner_id"]
    readonly_fields = ["future_lms_user_id", "future_lms_learner_id", "lms_linked_at"]
    def attempt_count(self, obj): return obj.attempts.count()

@admin.register(PMPQuestion)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["short_text", "performance_domain", "eco_domain", "eco_task", "question_type", "methodology", "has_exhibit", "source_year", "is_synthetic", "is_active", "import_status", "created_at"]
    list_filter = ["performance_domain", "eco_domain", "question_type", "methodology", "difficulty", "source_year", "is_synthetic", "is_active", "import_status"]
    search_fields = ["question_text", "question_id", "source_file", "source_sheet", "source_item_id", "eco_task", "exhibit_blob_name", "exhibits__title"]
    inlines = [OptionInline, QuestionExhibitInline]
    fieldsets = [
        ("Primary classification", {"fields": ["performance_domain", "question_type", "is_active", "is_synthetic", "import_status", "duplicate_of"]}),
        ("Question", {"fields": ["question_id", "question_text", "case_group_id", "case_text", "methodology", "difficulty"]}),
        ("Exhibit", {"fields": ["exhibit_blob_name", "exhibit_alt_text"]}),
        ("ECO metadata", {"fields": ["eco_domain", "eco_task", "domain", "topic", "task"]}),
        ("Explanations", {"fields": ["correct_answer_explanation", "wrong_answer_explanation"]}),
        ("Source", {"fields": ["source_file", "source_sheet", "source_year", "source_item_id", "pmp_reference", "chapter_reference"]}),
    ]
    def short_text(self, obj): return obj.question_text[:80]
    def has_exhibit(self, obj): return bool(obj.exhibit_blob_name or obj.exhibits.exists())
    has_exhibit.boolean = True

@admin.register(PMPExhibit)
class PMPExhibitAdmin(admin.ModelAdmin):
    list_display = ["title", "exhibit_type", "storage_backend", "source_exam", "source_question_number", "source_label", "question_count", "created_at"]
    list_filter = ["exhibit_type", "storage_backend", "source_exam"]
    search_fields = ["title", "source_label", "storage_path", "content", "questions__question_id", "questions__question_text"]
    inlines = [ExhibitQuestionInline]
    readonly_fields = ["checksum", "created_at", "updated_at"]
    def question_count(self, obj): return obj.questions.count()

admin.site.register([PMPAuthToken, PMPDomain, PMPTopic, PMPExamAttempt, PMPExamAttemptQuestion, PMPExamAnswer, PMPAIReport])
