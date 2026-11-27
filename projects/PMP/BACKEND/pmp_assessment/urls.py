from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("admin/questions", views.AdminQuestionViewSet, basename="pmp-admin-questions")
router.register("admin/profiles", views.AdminProfileViewSet, basename="pmp-admin-profiles")
router.register("admin/kbc-registry", views.KBCRegistryViewSet, basename="pmp-admin-kbc-registry")

urlpatterns = [
    path("csrf/", views.csrf_token),
    path("auth/register/", views.register), path("auth/login/", views.login_view), path("auth/logout/", views.logout_view),
    path("auth/verify-email/", views.verify_email), path("auth/password-reset/", views.password_reset_request), path("auth/password-reset/confirm/", views.password_reset_confirm),
    path("me/", views.me), path("dashboard/", views.dashboard),
    path("exhibits/<path:blob_name>/", views.question_exhibit, name="pmp-exhibit"),
    path("exhibit-assets/<int:exhibit_id>/", views.exhibit_asset, name="pmp-exhibit-asset"),
    path("learners/", views.LearnerCreateView.as_view()), path("domains/", views.DomainListView.as_view()), path("topics/", views.TopicListView.as_view()),
    path("attempts/", views.attempts), path("attempts/latest/report/", views.latest_report), path("attempts/latest/report/pdf/", views.latest_report_pdf),
    path("attempts/<int:pk>/", views.attempt_detail), path("attempts/<int:pk>/questions/", views.attempt_questions),
    path("attempts/<int:pk>/answers/<int:question_id>/", views.save_answer), path("attempts/<int:pk>/questions/<int:question_id>/review/", views.review_attempt_question), path("attempts/<int:pk>/submit/", views.submit_attempt),
    path("attempts/<int:pk>/abandon/", views.abandon_attempt),
    path("attempts/<int:pk>/result/", views.attempt_result), path("attempts/<int:pk>/generate-report/", views.generate_attempt_report),
    path("attempts/<int:pk>/report/", views.attempt_report), path("attempts/<int:pk>/report/pdf/", views.attempt_report_pdf),
    path("admin/questions/import/", views.import_questions), path("", include(router.urls)),
]
