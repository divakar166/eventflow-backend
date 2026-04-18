import uuid
from django.db import models
from apps.organizations.models import Tenant
from apps.events.models import Registration


class Invoice(models.Model):

    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        PAID      = 'paid',      'Paid'
        REFUNDED  = 'refunded',  'Refunded'
        FAILED    = 'failed',    'Failed'

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization     = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invoices')
    registration     = models.OneToOneField(Registration, on_delete=models.CASCADE, related_name='invoice')
    amount           = models.DecimalField(max_digits=10, decimal_places=2)
    currency         = models.CharField(max_length=3, default='usd')
    status           = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # Stripe fields
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    stripe_charge_id         = models.CharField(max_length=255, blank=True)
    # Idempotency — never process the same webhook event twice
    stripe_event_id          = models.CharField(max_length=255, blank=True, unique=True, null=True)
    paid_at          = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'payments'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['stripe_payment_intent_id']),
        ]

    def __str__(self):
        return f"Invoice {self.id} — {self.status}"