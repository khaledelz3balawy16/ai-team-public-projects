from django.contrib import admin

from .models import (
    Applicant, Application, ApplicationAnswer, ApplicationStatusHistory, CVDocument,
    Event, Question, QuestionCondition, QuestionOption, Track,
)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status", "applications_open_at", "applications_close_at")
    list_filter = ("status",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("name", "event", "code", "is_active", "display_order")
    list_filter = ("event", "is_active")
    search_fields = ("name", "code")
    list_select_related = ("event",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "track", "question_type", "is_required", "is_active", "display_order")
    list_filter = ("track__event", "track", "question_type", "is_active")
    search_fields = ("key", "title")
    list_select_related = ("track",)


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "question", "is_active", "display_order")
    list_filter = ("question__track", "is_active")
    search_fields = ("label", "value", "question__key")
    list_select_related = ("question",)

    def has_delete_permission(self, request, obj=None):
        # JSON responses reference stable values. Deactivate instead of deleting.
        return False


@admin.register(QuestionCondition)
class QuestionConditionAdmin(admin.ModelAdmin):
    list_display = ("target_question", "source_question", "operator", "expected_value")
    list_filter = ("target_question__track", "operator")
    search_fields = ("target_question__key", "source_question__key")
    list_select_related = ("target_question", "source_question")


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "email", "university", "education_status", "city")
    list_filter = ("education_status", "city")
    search_fields = ("full_name", "email", "mobile_number", "university")
    readonly_fields = ("id", "created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        # A retention workflow must coordinate private storage and application data.
        return False


class ReadOnlyAdmin(admin.ModelAdmin):
    actions = None

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Application)
class ApplicationAdmin(ReadOnlyAdmin):
    # Status changes require an atomic, attributed Phase 2 workflow. Inspection only.
    list_display = ("id", "event", "applicant", "track", "status", "submitted_at")
    list_filter = ("event", "track", "status", "opportunity_type")
    search_fields = ("=id", "applicant__full_name", "applicant__email")
    list_select_related = ("event", "track", "applicant")


@admin.register(ApplicationAnswer)
class ApplicationAnswerAdmin(ReadOnlyAdmin):
    list_display = ("id", "application", "question", "updated_at")
    list_filter = ("question__track",)
    search_fields = ("=application__id", "question__key")
    list_select_related = ("application", "question")


@admin.register(CVDocument)
class CVDocumentAdmin(ReadOnlyAdmin):
    list_display = ("id", "application", "file_extension", "size_bytes", "security_scan_status", "uploaded_at")
    list_filter = ("security_scan_status", "file_extension")
    search_fields = ("=application__id", "=id")
    list_select_related = ("application",)
    # Metadata only. No FileField, public URL, download link or storage endpoint.


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(ReadOnlyAdmin):
    list_display = ("application", "previous_status", "new_status", "changed_by", "changed_at")
    list_filter = ("new_status", "changed_at")
    search_fields = ("=application__id",)
    list_select_related = ("application", "changed_by")
