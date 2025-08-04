from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    Supports multi-tenant architecture with role-based access
    """
    ROLE_CHOICES = (
        ('super_admin', 'Super Admin'),
        ('pg_admin', 'PG Admin'),
        ('guest', 'Guest'),
    )
    
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='guest')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    pg = models.ForeignKey('hostel.PG', on_delete=models.CASCADE, null=True, blank=True)
    is_approved = models.BooleanField(default=False)  # For PG Admin approval
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def is_pg_admin(self):
        return self.role == 'pg_admin'
    
    def is_guest(self):
        return self.role == 'guest'
    
    class Meta:
        db_table = 'custom_user'