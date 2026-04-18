from celery import shared_task
from apps.organizations.tasks import tenant_task
from django.core.cache import cache


@shared_task
def precompute_all_tenant_analytics():
    """
    Runs nightly via Celery beat.
    Pre-warms the analytics cache for every active tenant
    so the first dashboard load of the day is instant.
    """
    from apps.organizations.models import Tenant

    tenants = Tenant.objects.filter(
        is_active=True
    ).exclude(schema_name='public')

    for tenant in tenants:
        precompute_tenant_analytics.delay(tenant.schema_name)


@shared_task
@tenant_task
def precompute_tenant_analytics(schema_name):
    """Warm analytics cache for a single tenant."""
    from apps.events.models import Event, Registration
    from apps.payments.models import Invoice
    from django.db.models import Count, Sum
    from django.utils import timezone
    from datetime import timedelta

    now         = timezone.now()
    thirty_days = now - timedelta(days=30)

    total_revenue = Invoice.objects.filter(
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_registrations = Registration.objects.filter(
        status=Registration.Status.CONFIRMED
    ).count()

    data = {
        'total_events'        : Event.objects.count(),
        'published_events'    : Event.objects.filter(status='published').count(),
        'upcoming_events'     : Event.objects.filter(
            status='published', start_datetime__gte=now
        ).count(),
        'total_registrations' : total_registrations,
        'total_revenue'       : str(total_revenue),
        'last_30_days'        : {
            'registrations': Registration.objects.filter(
                status=Registration.Status.CONFIRMED,
                registered_at__gte=thirty_days,
            ).count(),
            'revenue': str(
                Invoice.objects.filter(
                    status='paid', paid_at__gte=thirty_days
                ).aggregate(total=Sum('amount'))['total'] or 0
            ),
        },
    }

    from apps.analytics.views import cache_key
    from apps.organizations.models import Tenant
    tenant = Tenant.objects.get(schema_name=schema_name)

    # Fake a tenant object with schema_name for cache_key helper
    class _T:
        pass
    t = _T()
    t.schema_name = schema_name

    cache.set(cache_key(t, 'summary'), data, timeout=60 * 60 * 8)
    return f"Cache warmed for {schema_name}"