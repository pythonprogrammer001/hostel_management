from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Registration URLs
    path('register/pg-admin/', views.pg_admin_register, name='pg_admin_register'),
    
    # Profile URLs
    path('profile/', views.profile, name='profile'),
    
    # AJAX URLs
    path('ajax/check-username/', views.check_username, name='check_username'),
    path('ajax/check-email/', views.check_email, name='check_email'),
]