import uuid
from django.db import models
from apps.organizations.models import Tenant


class Event(models.Model):

    class Status(models.TextChoices):
        DRAFT       = 'draft',      'Draft'
        PUBLISHED   = 'published',  'Published'
        CANCELLED   = 'cancelled',  'Cancelled'
        COMPLETED   = 'completed',  'Completed'

    organization    = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='events')
    name            = models.CharField(max_length=255)
    description     = models.TextField(blank=True)
    venue           = models.CharField(max_length=255, blank=True)
    start_datetime  = models.DateTimeField()
    end_datetime    = models.DateTimeField()
    capacity        = models.PositiveIntegerField(default=0, help_text='0 = unlimited')
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_recurring    = models.BooleanField(default=False)
    recurrence_rule = models.CharField(max_length=255, blank=True, help_text='rrule string')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'events'
        ordering = ['-start_datetime']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['start_datetime']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_sold_out(self):
        if self.capacity == 0:
            return False
        total_registered = self.registrations.filter(
            status=Registration.Status.CONFIRMED
        ).count()
        return total_registered >= self.capacity


class TicketType(models.Model):

    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    quantity    = models.PositiveIntegerField(default=0, help_text='0 = unlimited')
    promo_code  = models.CharField(max_length=50, blank=True)
    promo_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'events'

    def __str__(self):
        return f"{self.name} — {self.event.name}"

    @property
    def available_quantity(self):
        if self.quantity == 0:
            return None   # unlimited
        sold = self.registrations.filter(
            status__in=[
                Registration.Status.CONFIRMED,
                Registration.Status.PENDING,
            ]
        ).count()
        return max(0, self.quantity - sold)


class Registration(models.Model):

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        ATTENDED  = 'attended',  'Attended'

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event           = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    ticket_type     = models.ForeignKey(TicketType, on_delete=models.SET_NULL, null=True, related_name='registrations')
    # Attendee info — not a User FK intentionally (public attendees don't need accounts)
    attendee_name   = models.CharField(max_length=255)
    attendee_email  = models.EmailField()
    attendee_phone  = models.CharField(max_length=20, blank=True)
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    qr_code         = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    notes           = models.TextField(blank=True)
    registered_at   = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'events'
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['attendee_email']),
        ]

    def __str__(self):
        return f"{self.attendee_name} → {self.event.name}"