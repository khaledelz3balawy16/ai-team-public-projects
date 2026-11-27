from django.urls import path
from . import auth_views

urlpatterns = [
    path('login/',    auth_views.login_redirect, name='login'),
    path('password-login/', auth_views.password_login, name='password-login'),
    path('callback/', auth_views.oauth_callback,  name='callback'),
    path('logout/',   auth_views.logout,           name='logout'),
    path('me/',       auth_views.me,               name='me'),
]
