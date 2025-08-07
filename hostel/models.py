from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.text import slugify
from decimal import Decimal


class PG(models.Model):
    """
    Central model representing each PG/Hostel property
    Each PG is managed by one PG Admin and contains multiple rooms and guests
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='owned_pg'
    )
    address = models.TextField()
    contact_phone = models.CharField(max_length=15)
    contact_email = models.EmailField()
    is_active = models.BooleanField(default=False)  # Super Admin activates this
    registration_date = models.DateTimeField(auto_now_add=True)
    subscription_plan = models.CharField(
        max_length=20, 
        choices=[('basic', 'Basic'), ('premium', 'Premium')], 
        default='basic'
    )
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while PG.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def get_occupancy_rate(self):
        """Calculate occupancy rate percentage"""
        total_rooms = self.room_set.count()
        if total_rooms == 0:
            return 0
        occupied_rooms = self.room_set.filter(guestprofile__isnull=False, guestprofile__check_out_date__isnull=True).count()
        return round((occupied_rooms / total_rooms) * 100, 2)
    
    def get_monthly_revenue(self):
        """Calculate current month's revenue"""
        from django.utils import timezone
        current_month = timezone.now().replace(day=1)
        bills = MonthlyBill.objects.filter(
            guest__user__pg=self,
            month_year=current_month,
            status='Paid'
        )
        return sum(bill.total_amount for bill in bills)
    
    class Meta:
        db_table = 'pg'


class Room(models.Model):
    """
    Room model linked to a PG
    Each room can accommodate one or more guests based on capacity
    """
    METER_TYPE_CHOICES = [
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
    ]
    
    pg = models.ForeignKey(PG, on_delete=models.CASCADE)
    room_number = models.CharField(max_length=10)
    capacity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    meter_type = models.CharField(max_length=10, choices=METER_TYPE_CHOICES, default='manual')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.pg.name} - Room {self.room_number}"
    
    def get_current_occupants(self):
        """Get current active guests in this room"""
        return self.guestprofile_set.filter(check_out_date__isnull=True)
    
    def is_full(self):
        """Check if room is at full capacity"""
        return self.get_current_occupants().count() >= self.capacity
    
    class Meta:
        db_table = 'room'
        unique_together = ['pg', 'room_number']


class GuestProfile(models.Model):
    """
    Guest profile model linked to CustomUser
    Contains all guest-specific information and room assignment
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    check_in_date = models.DateField()
    check_out_date = models.DateField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=15)
    id_proof_type = models.CharField(
        max_length=20,
        choices=[
            ('aadhar', 'Aadhar Card'),
            ('passport', 'Passport'),
            ('driving_license', 'Driving License'),
            ('voter_id', 'Voter ID'),
        ]
    )
    id_proof_number = models.CharField(max_length=50)
    id_proof_document = models.FileField(upload_to='documents/id_proofs/', null=True, blank=True)
    profile_photo = models.ImageField(upload_to='photos/guests/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.room}"
    
    def is_active(self):
        """Check if guest is currently active (not checked out)"""
        return self.check_out_date is None
    
    def get_pending_bills(self):
        """Get all unpaid bills for this guest"""
        return self.monthlybill_set.filter(status='Unpaid')
    
    def get_total_pending_amount(self):
        """Calculate total pending amount"""
        return sum(bill.total_amount for bill in self.get_pending_bills())
    
    class Meta:
        db_table = 'guest_profile'


class SecurityDeposit(models.Model):
    """
    Security deposit tracking for each guest
    """
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
        ('Refunded', 'Refunded'),
        ('Adjusted', 'Adjusted'),
    ]
    
    guest = models.OneToOneField(GuestProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    paid_date = models.DateField(null=True, blank=True)
    refund_date = models.DateField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.guest.user.get_full_name()} - ₹{self.amount} ({self.status})"
    
    class Meta:
        db_table = 'security_deposit'


class GuestHistory(models.Model):
    """
    Historical record of guest room assignments and rent changes
    """
    guest = models.ForeignKey(GuestProfile, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True)
    rent_at_the_time = models.DecimalField(max_digits=10, decimal_places=2)
    from_date = models.DateField()
    to_date = models.DateField()
    reason = models.CharField(
        max_length=50,
        choices=[
            ('room_change', 'Room Change'),
            ('rent_revision', 'Rent Revision'),
            ('checkout', 'Check Out'),
        ]
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.guest.user.get_full_name()} - {self.room} ({self.from_date} to {self.to_date})"
    
    class Meta:
        db_table = 'guest_history'
        ordering = ['-from_date']


class MonthlyBill(models.Model):
    """
    Monthly billing for guests including rent and additional charges
    """
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Partially_Paid', 'Partially Paid'),
        ('Overdue', 'Overdue'),
    ]
    
    guest = models.ForeignKey(GuestProfile, on_delete=models.CASCADE)
    month_year = models.DateField()  # First day of the billing month
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    electricity_units = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    electricity_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    electricity_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    water_charges = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    maintenance_charges = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    other_charges_description = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Unpaid')
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Cash'),
            ('bank_transfer', 'Bank Transfer'),
            ('upi', 'UPI'),
            ('cheque', 'Cheque'),
        ],
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.guest.user.get_full_name()} - {self.month_year.strftime('%B %Y')}"
    
    def save(self, *args, **kwargs):
        # Calculate total amount
        self.total_amount = (
            self.rent_amount + 
            self.electricity_amount + 
            self.water_charges + 
            self.maintenance_charges + 
            self.other_charges
        )
        
        # Update status based on payment
        if self.paid_amount >= self.total_amount:
            self.status = 'Paid'
        elif self.paid_amount > 0:
            self.status = 'Partially_Paid'
        else:
            self.status = 'Unpaid'
            
        super().save(*args, **kwargs)
    
    def get_balance_amount(self):
        """Get remaining balance amount"""
        return self.total_amount - self.paid_amount
    
    class Meta:
        db_table = 'monthly_bill'
        unique_together = ['guest', 'month_year']
        ordering = ['-month_year']


class Expense(models.Model):
    """
    Expense tracking for PG Admin
    """
    CATEGORY_CHOICES = [
        ('salary', 'Salary'),
        ('electricity', 'Electricity'),
        ('water', 'Water'),
        ('maintenance', 'Maintenance'),
        ('cleaning', 'Cleaning'),
        ('security', 'Security'),
        ('internet', 'Internet'),
        ('groceries', 'Groceries'),
        ('repairs', 'Repairs'),
        ('other', 'Other'),
    ]
    
    pg = models.ForeignKey(PG, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    date = models.DateField()
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.pg.name} - {self.get_category_display()} - ₹{self.amount}"
    
    class Meta:
        db_table = 'expense'
        ordering = ['-date']


class Issue(models.Model):
    """
    Issue tracking system for guests to report problems
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    CATEGORY_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('cleaning', 'Cleaning'),
        ('security', 'Security'),
        ('internet', 'Internet'),
        ('other', 'Other'),
    ]
    
    guest = models.ForeignKey(GuestProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='assigned_issues'
    )
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.guest.user.get_full_name()}"
    
    class Meta:
        db_table = 'issue'
        ordering = ['-created_at']