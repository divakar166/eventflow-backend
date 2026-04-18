from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_checkin_update(event_id, schema_name):
    """
    Call this from a Celery task after marking a registration as attended.
    Pushes live stats to all clients watching this event's check-in screen.
    """
    from django_tenants.utils import schema_context
    from apps.events.models import Event, Registration

    with schema_context(schema_name):
        try:
            event    = Event.objects.get(id=event_id)
            confirmed = event.registrations.filter(
                status=Registration.Status.CONFIRMED
            ).count()
            attended  = event.registrations.filter(
                status=Registration.Status.ATTENDED
            ).count()
        except Event.DoesNotExist:
            return

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"checkin_{event_id}",
        {
            'type'      : 'checkin.update',
            'event_id'  : event_id,
            'confirmed' : confirmed,
            'attended'  : attended,
            'capacity'  : event.capacity,
        }
    )


def broadcast_dashboard_update(schema_name, tenant):
    """
    Call this from a Celery task after a payment is confirmed.
    Pushes updated revenue/registration metrics to the admin dashboard.
    """
    from django_tenants.utils import schema_context
    from apps.events.models import Registration
    from apps.payments.models import Invoice
    from django.db.models import Sum

    with schema_context(schema_name):
        total_registrations = Registration.objects.filter(
            status=Registration.Status.CONFIRMED
        ).count()
        total_revenue = Invoice.objects.filter(
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"dashboard_{schema_name}",
        {
            'type'                : 'dashboard.update',
            'total_registrations' : total_registrations,
            'total_revenue'       : str(total_revenue),
        }
    )