from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("admin/", admin.site.urls), 
    path("api/pmp/", include("pmp_assessment.urls"))
    ]
