from django.urls import path
from . import views

app_name = 'hostel'

urlpatterns = [
    # PG Admin URLs
    path('<int:pg_id>/dashboard/', views.pg_admin_dashboard, name='pg_dashboard'),
    path('<int:pg_id>/guests/', views.guest_list, name='guest_list'),
    path('<int:pg_id>/guests/check-in/', views.guest_check_in, name='guest_check_in'),
    path('<int:pg_id>/guests/<int:guest_id>/', views.guest_detail, name='guest_detail'),
    path('<int:pg_id>/rooms/', views.room_management, name='room_management'),
    path('<int:pg_id>/billing/', views.billing_page, name='billing_page'),
    path('<int:pg_id>/billing/generate/', views.generate_bills, name='generate_bills'),
    path('<int:pg_id>/expenses/', views.expense_tracking, name='expense_tracking'),
    path('<int:pg_id>/issues/', views.issue_tracking, name='issue_tracking'),
    
    # Guest URLs
    path('<int:pg_id>/guest-dashboard/', views.guest_dashboard, name='guest_dashboard'),
    
    # AJAX URLs
    path('<int:pg_id>/ajax/update-bill/<int:bill_id>/', views.update_bill_payment, name='update_bill_payment'),
    path('<int:pg_id>/ajax/update-issue/<int:issue_id>/', views.update_issue_status, name='update_issue_status'),
]