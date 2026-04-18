import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from apps.organizations.models import Domain


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload    = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    # Stripe sends the tenant domain in metadata — set this when
    # creating PaymentIntents: metadata={'tenant_domain': 'acme.localhost'}
    metadata    = event.data.object.get('metadata', {})
    tenant_domain = metadata.get('tenant_domain')

    if not tenant_domain:
        return HttpResponse(status=200)  # not our event, ignore

    try:
        domain = Domain.objects.select_related('tenant').get(domain=tenant_domain)
        schema_name = domain.tenant.schema_name
    except Domain.DoesNotExist:
        return HttpResponse(status=200)

    payment_intent_id = event.data.object.get('id')
    stripe_event_id   = event.id

    from .tasks import handle_payment_success, handle_payment_failed

    if event.type == 'payment_intent.succeeded':
        handle_payment_success.delay(schema_name, stripe_event_id, payment_intent_id)

    elif event.type == 'payment_intent.payment_failed':
        handle_payment_failed.delay(schema_name, stripe_event_id, payment_intent_id)

    # Always return 200 immediately — never make Stripe wait for task completion
    return HttpResponse(status=200)