from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',               views.dashboard,              name='dashboard'),
    path('career-path/shown/',       views.career_path_shown,      name='career-path-shown'),
    path('career-path/save/',        views.career_path_save,       name='career-path-save'),
    path('career-path/generate/',    views.career_path_generate,   name='career-path-generate'),
    path('assessment/questions/',    views.assessment_questions,   name='assessment-questions'),
    path('assessment/submit/',       views.assessment_submit,      name='assessment-submit'),
    path('assessment/save/',         views.assessment_save,        name='assessment-save'),
]
