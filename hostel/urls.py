from django.urls import path
from . import views

app_name = 'hostel'

urlpatterns = [
    # Guest registration URLs (public)
    path('<str:pg_slug>/register/', views.guest_register, name='guest_register'),
    path('<str:pg_slug>/login/', views.pg_login, name='pg_login'),
    
    # PG Admin URLs
    path('<str:pg_slug>/dashboard/', views.pg_admin_dashboard, name='pg_dashboard'),
    path('<str:pg_slug>/guests/', views.guest_list, name='guest_list'),
    path('<str:pg_slug>/guests/check-in/', views.guest_check_in, name='guest_check_in'),
    path('<str:pg_slug>/guests/<int:guest_id>/', views.guest_detail, name='guest_detail'),
    path('<str:pg_slug>/rooms/', views.room_management, name='room_management'),
    path('<str:pg_slug>/billing/', views.billing_page, name='billing_page'),
    path('<str:pg_slug>/billing/generate/', views.generate_bills, name='generate_bills'),
    path('<str:pg_slug>/expenses/', views.expense_tracking, name='expense_tracking'),
    path('<str:pg_slug>/issues/', views.issue_tracking, name='issue_tracking'),
    
    # Guest URLs
    path('<str:pg_slug>/guest-dashboard/', views.guest_dashboard, name='guest_dashboard'),
    
    # AJAX URLs
    path('<str:pg_slug>/ajax/update-bill/<int:bill_id>/', views.update_bill_payment, name='update_bill_payment'),
    path('<str:pg_slug>/ajax/update-issue/<int:issue_id>/', views.update_issue_status, name='update_issue_status'),
    path('<str:pg_slug>/ajax/approve-guest/', views.approve_guest, name='approve_guest'),
    path('<str:pg_slug>/ajax/reject-guest/', views.reject_guest, name='reject_guest'),
]