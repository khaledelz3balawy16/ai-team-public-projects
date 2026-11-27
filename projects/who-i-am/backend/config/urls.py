from django.urls import path, include

urlpatterns = [
    path('api/auth/', include('psycho.auth_urls')),
    path('api/', include('psycho.urls')),
]
