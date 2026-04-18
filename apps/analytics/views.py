from django.core.cache import cache
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from datetime import timedelta

from apps.organizations.permissions import IsOrgAdmin, IsTenantMember
from apps.events.models import Event, Registration
from apps.payments.models import Invoice


def cache_key(tenant, suffix):
    """Namespaced cache key per tenant so tenants never see each other's data."""
    return f"analytics:{tenant.schema_name}:{suffix}"


@api_view(['GET'])
@permission_classes([IsTenantMember])
def summary(request):
    """
    High-level dashboard metrics. Cached per tenant for 10 minutes.
    GET /api/v1/analytics/summary/
    """
    key      = cache_key(request.tenant, 'summary')
    cached   = cache.get(key)
    if cached:
        return Response({**cached, 'from_cache': True})

    now         = timezone.now()
    thirty_days = now - timedelta(days=30)

    total_events        = Event.objects.filter(
        organization=request.tenant
    ).count()

    published_events    = Event.objects.filter(
        organization=request.tenant,
        status=Event.Status.PUBLISHED,
    ).count()

    total_registrations = Registration.objects.filter(
        event__organization=request.tenant,
        status=Registration.Status.CONFIRMED,
    ).count()

    total_revenue       = Invoice.objects.filter(
        organization=request.tenant,
        status=Invoice.Status.PAID,
    ).aggregate(total=Sum('amount'))['total'] or 0

    recent_registrations = Registration.objects.filter(
        event__organization=request.tenant,
        status=Registration.Status.CONFIRMED,
        registered_at__gte=thirty_days,
    ).count()

    recent_revenue      = Invoice.objects.filter(
        organization=request.tenant,
        status=Invoice.Status.PAID,
        paid_at__gte=thirty_days,
    ).aggregate(total=Sum('amount'))['total'] or 0

    upcoming_events     = Event.objects.filter(
        organization=request.tenant,
        status=Event.Status.PUBLISHED,
        start_datetime__gte=now,
    ).count()

    data = {
        'total_events'          : total_events,
        'published_events'      : published_events,
        'upcoming_events'       : upcoming_events,
        'total_registrations'   : total_registrations,
        'total_revenue'         : str(total_revenue),
        'last_30_days'          : {
            'registrations' : recent_registrations,
            'revenue'       : str(recent_revenue),
        },
    }

    cache.set(key, data, timeout=60 * 10)   # cache 10 min
    return Response({**data, 'from_cache': False})


@api_view(['GET'])
@permission_classes([IsTenantMember])
def registrations_over_time(request):
    """
    Daily registration counts for the last N days.
    GET /api/v1/analytics/registrations-over-time/?days=30
    """
    days    = min(int(request.query_params.get('days', 30)), 90)
    key     = cache_key(request.tenant, f'reg_over_time:{days}')
    cached  = cache.get(key)
    if cached:
        return Response({'data': cached, 'from_cache': True})

    since = timezone.now() - timedelta(days=days)

    qs = (
        Registration.objects
        .filter(
            event__organization=request.tenant,
            status=Registration.Status.CONFIRMED,
            registered_at__gte=since,
        )
        .annotate(day=TruncDay('registered_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    data = [
        {'date': entry['day'].strftime('%Y-%m-%d'), 'count': entry['count']}
        for entry in qs
    ]

    cache.set(key, data, timeout=60 * 15)
    return Response({'data': data, 'from_cache': False})


@api_view(['GET'])
@permission_classes([IsTenantMember])
def revenue_over_time(request):
    """
    Monthly revenue totals.
    GET /api/v1/analytics/revenue-over-time/?months=6
    """
    months  = min(int(request.query_params.get('months', 6)), 12)
    key     = cache_key(request.tenant, f'revenue_over_time:{months}')
    cached  = cache.get(key)
    if cached:
        return Response({'data': cached, 'from_cache': True})

    since = timezone.now() - timedelta(days=months * 30)

    qs = (
        Invoice.objects
        .filter(
            organization=request.tenant,
            status=Invoice.Status.PAID,
            paid_at__gte=since,
        )
        .annotate(month=TruncMonth('paid_at'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    data = [
        {'month': entry['month'].strftime('%Y-%m'), 'revenue': str(entry['total'])}
        for entry in qs
    ]

    cache.set(key, data, timeout=60 * 15)
    return Response({'data': data, 'from_cache': False})


@api_view(['GET'])
@permission_classes([IsTenantMember])
def top_events(request):
    """
    Events ranked by registration count.
    GET /api/v1/analytics/top-events/?limit=5
    """
    limit   = min(int(request.query_params.get('limit', 5)), 20)
    key     = cache_key(request.tenant, f'top_events:{limit}')
    cached  = cache.get(key)
    if cached:
        return Response({'data': cached, 'from_cache': True})

    qs = (
        Event.objects
        .filter(organization=request.tenant)
        .annotate(registration_count=Count(
            'registrations',
            filter=__import__('django.db.models', fromlist=['Q']).Q(
                registrations__status=Registration.Status.CONFIRMED
            )
        ))
        .order_by('-registration_count')[:limit]
    )

    data = [
        {
            'event_id'           : e.id,
            'event_name'         : e.name,
            'registration_count' : e.registration_count,
            'start_datetime'     : e.start_datetime.isoformat(),
            'status'             : e.status,
        }
        for e in qs
    ]

    cache.set(key, data, timeout=60 * 10)
    return Response({'data': data, 'from_cache': False})


@api_view(['GET'])
@permission_classes([IsTenantMember])
def ticket_type_breakdown(request):
    """
    Registration count and revenue per ticket type across all events.
    GET /api/v1/analytics/ticket-breakdown/
    """
    key    = cache_key(request.tenant, 'ticket_breakdown')
    cached = cache.get(key)
    if cached:
        return Response({'data': cached, 'from_cache': True})

    from apps.events.models import TicketType

    qs = (
        TicketType.objects
        .filter(event__organization=request.tenant)
        .annotate(
            confirmed_count=Count(
                'registrations',
                filter=__import__('django.db.models', fromlist=['Q']).Q(
                    registrations__status=Registration.Status.CONFIRMED
                )
            )
        )
        .values('name', 'price', 'confirmed_count')
        .order_by('-confirmed_count')
    )

    data = list(qs)
    cache.set(key, data, timeout=60 * 10)
    return Response({'data': data, 'from_cache': False})


@api_view(['POST'])
@permission_classes([IsOrgAdmin])
def invalidate_cache(request):
    """
    Manually bust analytics cache for this tenant.
    POST /api/v1/analytics/invalidate-cache/
    Useful after bulk data imports or corrections.
    """
    suffixes = [
        'summary', 'ticket_breakdown',
        'reg_over_time:30', 'reg_over_time:60', 'reg_over_time:90',
        'revenue_over_time:3', 'revenue_over_time:6', 'revenue_over_time:12',
        'top_events:5', 'top_events:10', 'top_events:20',
    ]
    for suffix in suffixes:
        cache.delete(cache_key(request.tenant, suffix))

    return Response({'invalidated': True})