from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import calendar

from .models import (
    PG, Room, GuestProfile, SecurityDeposit, 
    GuestHistory, MonthlyBill, Expense, Issue
)
from accounts.models import CustomUser
from .forms import (
    GuestRegistrationForm, GuestCheckInForm, RoomForm, ExpenseForm, 
    IssueForm, MonthlyBillForm, GuestProfileUpdateForm
)


def pg_required(view_func):
    """
    Decorator to ensure user has access to the specified PG
    """
    def wrapper(request, pg_slug, *args, **kwargs):
        pg = get_object_or_404(PG, slug=pg_slug)
        
        # Super admin can access all PGs
        if request.user.is_superuser:
            return view_func(request, pg_slug, *args, **kwargs)
        
        # PG Admin can only access their own PG
        if request.user.is_pg_admin():
            if (hasattr(request.user, 'owned_pg') and 
                request.user.owned_pg.slug == pg.slug and 
                request.user.is_approved and 
                request.user.owned_pg.is_active):
                return view_func(request, pg_slug, *args, **kwargs)
            elif not request.user.is_approved:
                messages.error(request, 'Your account is pending approval from the administrator.')
                return redirect('accounts:login')
            elif not request.user.owned_pg.is_active:
                messages.error(request, 'Your PG is not activated yet. Please contact the administrator.')
                return redirect('accounts:login')
        
        # Guest can only access their assigned PG
        if request.user.is_guest():
            if (request.user.pg and 
                request.user.pg.slug == pg.slug and 
                request.user.is_approved):
                return view_func(request, pg_slug, *args, **kwargs)
            elif not request.user.is_approved:
                messages.error(request, 'Your account is pending approval from the PG administrator.')
                return redirect('hostel:pg_login', pg_slug=pg_slug)
        
        return HttpResponseForbidden("You don't have permission to access this PG.")
    
    return wrapper


def guest_register(request, pg_slug):
    """
    Guest self-registration for a specific PG
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    if not pg.is_active:
        messages.error(request, f'{pg.name} is not currently accepting new registrations.')
        return render(request, 'hostel/guest_register.html', {'form': GuestRegistrationForm(), 'pg': pg})
    
    if request.method == 'POST':
        form = GuestRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            # Create user account for guest
            user = form.save(commit=False)
            user.role = 'guest'
            user.pg = pg
            user.is_approved = False  # Requires PG Admin approval
            user.save()
            
            # Create guest profile
            guest_profile = GuestProfile.objects.create(
                user=user,
                rent_amount=0,  # Will be set by PG admin
                check_in_date=timezone.now().date(),
                emergency_contact_name=form.cleaned_data['emergency_contact_name'],
                emergency_contact_phone=form.cleaned_data['emergency_contact_phone'],
                id_proof_type=form.cleaned_data['id_proof_type'],
                id_proof_number=form.cleaned_data['id_proof_number'],
                id_proof_document=form.cleaned_data['id_proof_document'],
                profile_photo=form.cleaned_data['profile_photo']
            )
            
            messages.success(
                request, 
                f'Registration successful! Your account is pending approval from {pg.name} administration.'
            )
            return redirect('hostel:pg_login', pg_slug=pg_slug)
    else:
        form = GuestRegistrationForm()
    
    return render(request, 'hostel/guest_register.html', {'form': form, 'pg': pg})


def pg_login(request, pg_slug):
    """
    Login page for a specific PG
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    if not pg.is_active:
        messages.error(request, f'{pg.name} is not currently active. Please contact the administrator.')
        return render(request, 'hostel/pg_login.html', {'pg': pg})
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.pg == pg:
                login(request, user)
                if user.is_pg_admin() and user.is_approved and pg.is_active:
                    return redirect('hostel:pg_dashboard', pg_slug=pg_slug)
                elif user.is_pg_admin() and not user.is_approved:
                    messages.error(request, 'Your account is pending approval from the administrator.')
                elif user.is_pg_admin() and not pg.is_active:
                    messages.error(request, 'Your PG is not activated yet. Please contact the administrator.')
                elif user.is_guest() and user.is_approved:
                    return redirect('hostel:guest_dashboard', pg_slug=pg_slug)
                elif user.is_guest() and not user.is_approved:
                    messages.error(request, 'Your account is pending approval from the PG administrator.')
            else:
                messages.error(request, 'Account not associated with this PG.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'hostel/pg_login.html', {'pg': pg})


@login_required
@pg_required
def pg_admin_dashboard(request, pg_slug):
    """
    Main dashboard for PG Admin
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    # Key metrics
    total_rooms = pg.room_set.count()
    occupied_rooms = Room.objects.filter(
        pg=pg, 
        guestprofile__isnull=False, 
        guestprofile__check_out_date__isnull=True
    ).count()
    occupancy_rate = pg.get_occupancy_rate()
    
    # Active guests
    active_guests = GuestProfile.objects.filter(
        user__pg=pg, 
        check_out_date__isnull=True
    ).select_related('user', 'room')
    
    # Monthly revenue
    current_month = timezone.now().replace(day=1)
    monthly_revenue = MonthlyBill.objects.filter(
        guest__user__pg=pg,
        month_year=current_month,
        status='Paid'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Pending dues
    pending_dues = MonthlyBill.objects.filter(
        guest__user__pg=pg,
        status__in=['Unpaid', 'Partially_Paid', 'Overdue']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Open issues
    open_issues_count = Issue.objects.filter(
        guest__user__pg=pg,
        status__in=['open', 'in_progress']
    ).count()
    
    # Recent activities (last 10)
    recent_checkins = GuestProfile.objects.filter(
        user__pg=pg
    ).order_by('-created_at')[:5]
    
    # Upcoming checkouts (next 30 days)
    upcoming_date = timezone.now().date() + timedelta(days=30)
    upcoming_checkouts = GuestProfile.objects.filter(
        user__pg=pg,
        check_out_date__lte=upcoming_date,
        check_out_date__gte=timezone.now().date()
    ).select_related('user', 'room')
    
    context = {
        'pg': pg,
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'occupancy_rate': occupancy_rate,
        'active_guests': active_guests,
        'monthly_revenue': monthly_revenue,
        'pending_dues': pending_dues,
        'open_issues_count': open_issues_count,
        'recent_checkins': recent_checkins,
        'upcoming_checkouts': upcoming_checkouts,
    }
    
    return render(request, 'hostel/pg_admin_dashboard.html', context)


@login_required
@pg_required
def guest_check_in(request, pg_slug):
    """
    Check-in new guest
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    if request.method == 'POST':
        form = GuestCheckInForm(request.POST, request.FILES, pg=pg)
        if form.is_valid():
            # Create user account for guest
            user = CustomUser.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address'],
                role='guest',
                pg=pg,
                is_approved=True
            )
            
            # Create guest profile
            guest_profile = GuestProfile.objects.create(
                user=user,
                room=form.cleaned_data['room'],
                rent_amount=form.cleaned_data['rent_amount'],
                check_in_date=form.cleaned_data['check_in_date'],
                emergency_contact_name=form.cleaned_data['emergency_contact_name'],
                emergency_contact_phone=form.cleaned_data['emergency_contact_phone'],
                id_proof_type=form.cleaned_data['id_proof_type'],
                id_proof_number=form.cleaned_data['id_proof_number'],
                id_proof_document=form.cleaned_data.get('id_proof_document'),
                profile_photo=form.cleaned_data.get('profile_photo')
            )
            
            # Create security deposit record
            SecurityDeposit.objects.create(
                guest=guest_profile,
                amount=form.cleaned_data['security_deposit'],
                status='Paid' if form.cleaned_data['deposit_paid'] else 'Pending',
                paid_date=form.cleaned_data['check_in_date'] if form.cleaned_data['deposit_paid'] else None
            )
            
            # Create initial guest history record
            GuestHistory.objects.create(
                guest=guest_profile,
                room=form.cleaned_data['room'],
                rent_at_the_time=form.cleaned_data['rent_amount'],
                from_date=form.cleaned_data['check_in_date'],
                to_date=form.cleaned_data['check_in_date'],  # Will be updated on checkout
                reason='room_change'
            )
            
            messages.success(request, f'Guest {user.get_full_name()} checked in successfully!')
            return redirect('hostel:guest_detail', pg_slug=pg_slug, guest_id=guest_profile.id)
    else:
        form = GuestCheckInForm(pg=pg)
    
    return render(request, 'hostel/guest_check_in.html', {'form': form, 'pg': pg})


@login_required
@pg_required
def guest_list(request, pg_slug):
    """
    List all guests for a PG
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    # Filter options
    status_filter = request.GET.get('status', 'active')
    search_query = request.GET.get('search', '')
    
    guests = GuestProfile.objects.filter(user__pg=pg).select_related('user', 'room')
    
    if status_filter == 'active':
        guests = guests.filter(check_out_date__isnull=True)
    elif status_filter == 'checked_out':
        guests = guests.filter(check_out_date__isnull=False)
    
    if search_query:
        guests = guests.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(room__room_number__icontains=search_query)
        )
    
    context = {
        'pg': pg,
        'guests': guests,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'hostel/guest_list.html', context)


@login_required
@pg_required
def guest_detail(request, pg_slug, guest_id):
    """
    Detailed view of a guest
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    guest = get_object_or_404(GuestProfile, id=guest_id, user__pg=pg)
    
    # Guest history
    history = GuestHistory.objects.filter(guest=guest).order_by('-from_date')
    
    # Bills
    bills = MonthlyBill.objects.filter(guest=guest).order_by('-month_year')
    
    # Security deposit
    try:
        security_deposit = SecurityDeposit.objects.get(guest=guest)
    except SecurityDeposit.DoesNotExist:
        security_deposit = None
    
    # Issues
    issues = Issue.objects.filter(guest=guest).order_by('-created_at')
    
    context = {
        'pg': pg,
        'guest': guest,
        'history': history,
        'bills': bills,
        'security_deposit': security_deposit,
        'issues': issues,
    }
    
    return render(request, 'hostel/guest_detail.html', context)


@login_required
@pg_required
def billing_page(request, pg_slug):
    """
    Billing management page
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    # Get current month or selected month
    selected_month = request.GET.get('month')
    if selected_month:
        try:
            selected_date = datetime.strptime(selected_month, '%Y-%m').date()
        except ValueError:
            selected_date = timezone.now().date().replace(day=1)
    else:
        selected_date = timezone.now().date().replace(day=1)
    
    # Get all bills for the selected month
    bills = MonthlyBill.objects.filter(
        guest__user__pg=pg,
        month_year=selected_date
    ).select_related('guest__user', 'guest__room')
    
    # Summary statistics
    total_bills = bills.count()
    total_amount = bills.aggregate(Sum('total_amount'))['total_amount'] or 0
    paid_amount = bills.aggregate(Sum('paid_amount'))['paid_amount'] or 0
    pending_amount = total_amount - paid_amount
    
    context = {
        'pg': pg,
        'bills': bills,
        'selected_date': selected_date,
        'total_bills': total_bills,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
    }
    
    return render(request, 'hostel/billing.html', context)


@login_required
@pg_required
def generate_bills(request, pg_slug):
    """
    Generate bills for all active guests for a specific month
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    if request.method == 'POST':
        month_year = request.POST.get('month_year')
        try:
            bill_date = datetime.strptime(month_year, '%Y-%m').date()
        except ValueError:
            messages.error(request, 'Invalid month format.')
            return redirect('hostel:billing_page', pg_id=pg_id)
        
        # Get all active guests
        active_guests = GuestProfile.objects.filter(
            user__pg=pg,
            check_out_date__isnull=True
        )
        
        bills_created = 0
        for guest in active_guests:
            # Check if bill already exists
            if not MonthlyBill.objects.filter(guest=guest, month_year=bill_date).exists():
                # Calculate due date (15th of next month)
                if bill_date.month == 12:
                    due_date = bill_date.replace(year=bill_date.year + 1, month=1, day=15)
                else:
                    due_date = bill_date.replace(month=bill_date.month + 1, day=15)
                
                MonthlyBill.objects.create(
                    guest=guest,
                    month_year=bill_date,
                    rent_amount=guest.rent_amount,
                    due_date=due_date
                )
                bills_created += 1
        
        messages.success(request, f'{bills_created} bills generated successfully!')
        return redirect('hostel:billing_page', pg_slug=pg_slug)
    
    return redirect('hostel:billing_page', pg_slug=pg_slug)


@login_required
@pg_required
def guest_dashboard(request, pg_slug):
    """
    Dashboard for guests
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    # Ensure user is a guest of this PG
    if not request.user.is_guest() or request.user.pg != pg:
        return HttpResponseForbidden("Access denied.")
    
    try:
        guest_profile = GuestProfile.objects.get(user=request.user)
    except GuestProfile.DoesNotExist:
        messages.error(request, 'Guest profile not found.')
        return redirect('accounts:login')
    
    # Get recent bills
    recent_bills = MonthlyBill.objects.filter(guest=guest_profile).order_by('-month_year')[:5]
    
    # Get pending bills
    pending_bills = MonthlyBill.objects.filter(
        guest=guest_profile,
        status__in=['Unpaid', 'Partially_Paid', 'Overdue']
    )
    
    # Get security deposit
    try:
        security_deposit = SecurityDeposit.objects.get(guest=guest_profile)
    except SecurityDeposit.DoesNotExist:
        security_deposit = None
    
    # Get recent issues
    recent_issues = Issue.objects.filter(guest=guest_profile).order_by('-created_at')[:5]
    
    context = {
        'pg': pg,
        'guest_profile': guest_profile,
        'recent_bills': recent_bills,
        'pending_bills': pending_bills,
        'security_deposit': security_deposit,
        'recent_issues': recent_issues,
    }
    
    return render(request, 'hostel/guest_dashboard.html', context)


@login_required
@pg_required
def room_management(request, pg_slug):
    """
    Room management page for PG Admin
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    rooms = Room.objects.filter(pg=pg).prefetch_related('guestprofile_set')
    
    context = {
        'pg': pg,
        'rooms': rooms,
    }
    
    return render(request, 'hostel/room_management.html', context)


@login_required
@pg_required
def expense_tracking(request, pg_slug):
    """
    Expense tracking page for PG Admin
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.pg = pg
            expense.created_by = request.user
            expense.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('hostel:expense_tracking', pg_slug=pg_slug)
    else:
        form = ExpenseForm()
    
    # Get expenses for current month
    current_month = timezone.now().date().replace(day=1)
    expenses = Expense.objects.filter(
        pg=pg,
        date__gte=current_month
    ).order_by('-date')
    
    # Calculate total for current month
    monthly_total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'pg': pg,
        'form': form,
        'expenses': expenses,
        'monthly_total': monthly_total,
    }
    
    return render(request, 'hostel/expense_tracking.html', context)


@login_required
@pg_required
def issue_tracking(request, pg_slug):
    """
    Issue tracking page
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    issues = Issue.objects.filter(guest__user__pg=pg)
    
    if status_filter != 'all':
        issues = issues.filter(status=status_filter)
    
    issues = issues.select_related('guest__user').order_by('-created_at')
    
    context = {
        'pg': pg,
        'issues': issues,
        'status_filter': status_filter,
    }
    
    return render(request, 'hostel/issue_tracking.html', context)


@require_http_methods(["POST"])
@login_required
@pg_required
def update_bill_payment(request, pg_slug, bill_id):
    """
    AJAX view to update bill payment status
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    bill = get_object_or_404(MonthlyBill, id=bill_id, guest__user__pg=pg)
    
    paid_amount = request.POST.get('paid_amount')
    payment_method = request.POST.get('payment_method')
    
    try:
        paid_amount = Decimal(paid_amount)
        bill.paid_amount = paid_amount
        bill.payment_method = payment_method
        if paid_amount > 0:
            bill.paid_date = timezone.now().date()
        bill.save()  # This will automatically update the status
        
        return JsonResponse({
            'success': True,
            'new_status': bill.get_status_display(),
            'balance': str(bill.get_balance_amount())
        })
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid amount'})


@require_http_methods(["POST"])
@login_required
@pg_required
def update_issue_status(request, pg_slug, issue_id):
    """
    AJAX view to update issue status
    """
    pg = get_object_or_404(PG, slug=pg_slug)
    issue = get_object_or_404(Issue, id=issue_id, guest__user__pg=pg)
    
    new_status = request.POST.get('status')
    resolution_notes = request.POST.get('resolution_notes', '')
    
    if new_status in dict(Issue.STATUS_CHOICES):
        issue.status = new_status
        if resolution_notes:
            issue.resolution_notes = resolution_notes
        if new_status == 'resolved':
            issue.resolved_at = timezone.now()
        issue.save()
        
        return JsonResponse({
            'success': True,
            'new_status': issue.get_status_display()
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid status'})