import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django_tenants.utils import schema_context


class CheckInConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live check-in updates.
    Connect: ws://acme.localhost:8000/ws/checkin/<event_id>/
    Pushes live attendee count whenever someone is marked as attended.
    """

    async def connect(self):
        self.event_id   = self.scope['url_route']['kwargs']['event_id']
        self.tenant     = self.scope.get('tenant')
        self.group_name = f"checkin_{self.event_id}"

        if not self.tenant:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send current count immediately on connect
        stats = await self.get_checkin_stats()
        await self.send(text_data=json.dumps({
            'type': 'checkin.stats',
            **stats,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Clients don't send anything — this is a push-only channel
        pass

    async def checkin_update(self, event):
        """Called by group_send from the task layer."""
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_checkin_stats(self):
        from apps.events.models import Event, Registration
        schema_name = self.tenant.schema_name

        with schema_context(schema_name):
            try:
                event = Event.objects.get(id=self.event_id)
                total      = event.registrations.filter(
                    status=Registration.Status.CONFIRMED
                ).count()
                attended   = event.registrations.filter(
                    status=Registration.Status.ATTENDED
                ).count()
                return {
                    'event_id'  : self.event_id,
                    'event_name': event.name,
                    'confirmed' : total,
                    'attended'  : attended,
                    'capacity'  : event.capacity,
                }
            except Event.DoesNotExist:
                return {'error': 'Event not found'}


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time admin dashboard metrics.
    Connect: ws://acme.localhost:8000/ws/dashboard/
    Pushes ticket sale milestones and revenue updates.
    """

    async def connect(self):
        self.tenant     = self.scope.get('tenant')
        self.group_name = f"dashboard_{self.tenant.schema_name}" if self.tenant else None

        if not self.tenant:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send current dashboard snapshot on connect
        snapshot = await self.get_dashboard_snapshot()
        await self.send(text_data=json.dumps({
            'type': 'dashboard.snapshot',
            **snapshot,
        }))

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def dashboard_update(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_dashboard_snapshot(self):
        from apps.events.models import Event, Registration
        from apps.payments.models import Invoice
        from django.db.models import Sum
        schema_name = self.tenant.schema_name

        with schema_context(schema_name):
            total_events       = Event.objects.filter(status='published').count()
            total_registrations = Registration.objects.filter(
                status=Registration.Status.CONFIRMED
            ).count()
            total_revenue      = Invoice.objects.filter(
                status='paid'
            ).aggregate(total=Sum('amount'))['total'] or 0

            return {
                'total_events'        : total_events,
                'total_registrations' : total_registrations,
                'total_revenue'       : str(total_revenue),
            }