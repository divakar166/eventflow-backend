from celery import shared_task
from django.utils import timezone
from apps.organizations.tasks import tenant_task


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
@tenant_task
def handle_payment_success(self, schema_name, stripe_event_id, payment_intent_id):
    from .models import Invoice
    from apps.events.models import Registration
    from apps.notifications.broadcast import broadcast_dashboard_update

    if Invoice.objects.filter(stripe_event_id=stripe_event_id).exists():
        return f"Event {stripe_event_id} already processed."

    try:
        invoice = Invoice.objects.select_related('registration').get(
            stripe_payment_intent_id=payment_intent_id
        )
    except Invoice.DoesNotExist:
        raise self.retry(exc=Exception(f"Invoice not found for {payment_intent_id}"))

    invoice.status          = Invoice.Status.PAID
    invoice.stripe_event_id = stripe_event_id
    invoice.paid_at         = timezone.now()
    invoice.save(update_fields=['status', 'stripe_event_id', 'paid_at'])

    invoice.registration.status = Registration.Status.CONFIRMED
    invoice.registration.save(update_fields=['status'])

    from apps.events.tasks import generate_qr_code
    generate_qr_code.delay(schema_name, str(invoice.registration.id))

    # Push real-time update to dashboard
    from apps.organizations.models import Tenant
    tenant = Tenant.objects.get(schema_name=schema_name)
    broadcast_dashboard_update(schema_name, tenant)

    return f"Invoice {invoice.id} marked paid."


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
@tenant_task
def handle_payment_failed(self, schema_name, stripe_event_id, payment_intent_id):
    from .models import Invoice

    if Invoice.objects.filter(stripe_event_id=stripe_event_id).exists():
        return f"Event {stripe_event_id} already processed."

    try:
        invoice = Invoice.objects.get(stripe_payment_intent_id=payment_intent_id)
    except Invoice.DoesNotExist:
        raise self.retry(exc=Exception(f"Invoice not found for {payment_intent_id}"))

    invoice.status          = Invoice.Status.FAILED
    invoice.stripe_event_id = stripe_event_id
    invoice.save(update_fields=['status', 'stripe_event_id'])

    return f"Invoice {invoice.id} marked failed."


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
@tenant_task
def process_refund(self, schema_name, invoice_id):
    """Trigger a Stripe refund and mark invoice as refunded."""
    import stripe
    from django.conf import settings
    from .models import Invoice

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return f"Invoice {invoice_id} not found."

    try:
        stripe.Refund.create(payment_intent=invoice.stripe_payment_intent_id)
        invoice.status = Invoice.Status.REFUNDED
        invoice.save(update_fields=['status'])
        return f"Invoice {invoice_id} refunded."
    except stripe.error.StripeError as exc:
        raise self.retry(exc=exc)