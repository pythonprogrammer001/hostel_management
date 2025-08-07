from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import IntegrityError
from .models import CustomUser
from hostel.models import PG
from .forms import PGAdminRegistrationForm, GuestRegistrationForm


def dashboard_redirect(request):
    """
    Redirect users to appropriate dashboard based on their role
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    if request.user.is_super_admin():
        return redirect('/admin/')
    elif request.user.is_pg_admin():
        if hasattr(request.user, 'owned_pg') and request.user.is_approved and request.user.owned_pg.is_active:
            return redirect('hostel:pg_dashboard', pg_slug=request.user.owned_pg.slug)
        elif hasattr(request.user, 'owned_pg') and not request.user.is_approved:
            messages.error(request, 'Your account is pending approval from the administrator.')
            return redirect('accounts:login')
        elif hasattr(request.user, 'owned_pg') and not request.user.owned_pg.is_active:
            messages.error(request, 'Your PG is not activated yet. Please contact the administrator.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'No PG associated with your account.')
            return redirect('accounts:login')
    elif request.user.is_guest():
        if request.user.pg and request.user.is_approved:
            return redirect('hostel:guest_dashboard', pg_slug=request.user.pg.slug)
        elif request.user.pg and not request.user.is_approved:
            messages.error(request, 'Your account is pending approval from the PG administrator.')
            return redirect('hostel:pg_login', pg_slug=request.user.pg.slug)
        else:
            messages.error(request, 'No PG associated with your account.')
            return redirect('accounts:login')
    else:
        messages.error(request, 'Invalid user role.')
        return redirect('accounts:login')


def pg_admin_register(request):
    """
    Registration view for PG Admins
    """
    if request.method == 'POST':
        form = PGAdminRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.role = 'pg_admin'
                user.is_approved = False  # Requires Super Admin approval
                user.is_active = True  # Allow login but restrict access
                user.save()
                
                # Create PG instance
                pg = PG.objects.create(
                    name=form.cleaned_data['pg_name'],
                    owner=user,
                    address=form.cleaned_data['pg_address'],
                    contact_phone=form.cleaned_data['contact_phone'],
                    contact_email=form.cleaned_data['contact_email'],
                    is_active=False  # Requires Super Admin activation
                )
                
                # Associate user with PG
                user.pg = pg
                user.save()
                
                messages.success(
                    request, 
                    'Registration successful! Your account is pending approval from the administrator. You cannot access the dashboard until approved.'
                )
                return redirect('accounts:login')
            except IntegrityError as e:
                if 'username' in str(e):
                    form.add_error('username', 'This username is already taken. Please choose a different one.')
                elif 'email' in str(e):
                    form.add_error('email', 'This email is already registered. Please use a different email.')
                else:
                    messages.error(request, 'Registration failed. Please check your information and try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PGAdminRegistrationForm()
    
    return render(request, 'accounts/pg_admin_register.html', {'form': form})


@login_required
def profile(request):
    """
    User profile view
    """
    return render(request, 'accounts/profile.html', {'user': request.user})


@require_http_methods(["POST"])
def check_username(request):
    """
    AJAX view to check if username is available
    """
    username = request.POST.get('username')
    is_taken = CustomUser.objects.filter(username=username).exists()
    return JsonResponse({'is_taken': is_taken})


@require_http_methods(["POST"])
def check_email(request):
    """
    AJAX view to check if email is available
    """
    email = request.POST.get('email')
    is_taken = CustomUser.objects.filter(email=email).exists()
    return JsonResponse({'is_taken': is_taken})