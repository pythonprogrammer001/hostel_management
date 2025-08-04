from django.contrib import admin
from .models import (
    PG, Room, GuestProfile, SecurityDeposit, 
    GuestHistory, MonthlyBill, Expense, Issue
)


@admin.register(PG)
class PGAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_active', 'subscription_plan', 'registration_date')
    list_filter = ('is_active', 'subscription_plan', 'registration_date')
    search_fields = ('name', 'owner__username', 'owner__email')
    readonly_fields = ('registration_date',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'pg', 'capacity', 'rent_amount', 'is_available')
    list_filter = ('pg', 'is_available', 'capacity')
    search_fields = ('room_number', 'pg__name')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'owned_pg'):
            return qs.filter(pg=request.user.owned_pg)
        return qs.none()


@admin.register(GuestProfile)
class GuestProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'rent_amount', 'check_in_date', 'check_out_date')
    list_filter = ('check_in_date', 'check_out_date', 'room__pg')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'owned_pg'):
            return qs.filter(user__pg=request.user.owned_pg)
        return qs.none()


@admin.register(SecurityDeposit)
class SecurityDepositAdmin(admin.ModelAdmin):
    list_display = ('guest', 'amount', 'status', 'paid_date')
    list_filter = ('status', 'paid_date')
    search_fields = ('guest__user__username', 'guest__user__first_name')


@admin.register(MonthlyBill)
class MonthlyBillAdmin(admin.ModelAdmin):
    list_display = ('guest', 'month_year', 'total_amount', 'paid_amount', 'status')
    list_filter = ('status', 'month_year')
    search_fields = ('guest__user__username', 'guest__user__first_name')
    readonly_fields = ('total_amount', 'created_at', 'updated_at')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('pg', 'category', 'amount', 'date', 'created_by')
    list_filter = ('category', 'date', 'pg')
    search_fields = ('description', 'pg__name')
    readonly_fields = ('created_at',)


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'guest', 'category', 'priority', 'status', 'created_at')
    list_filter = ('category', 'priority', 'status', 'created_at')
    search_fields = ('title', 'description', 'guest__user__username')
    readonly_fields = ('created_at', 'updated_at')