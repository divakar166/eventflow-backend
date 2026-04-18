from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.organizations.viewsets import TenantModelViewSet
from apps.organizations.permissions import IsOrgAdmin, IsEventManager
from .models import Event, TicketType, Registration
from .serializers import EventSerializer, TicketTypeSerializer, RegistrationSerializer


class EventViewSet(TenantModelViewSet):
    serializer_class = EventSerializer
    queryset         = Event.objects.prefetch_related('ticket_types').all()
    tenant_field     = 'organization'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'bulk_publish']:
            return [IsEventManager()]
        return super().get_permissions()   # IsTenantMember for list/retrieve

    @action(detail=False, methods=['post'], permission_classes=[IsEventManager])
    def bulk_publish(self, request):
        """Publish multiple events at once. Body: {"event_ids": [1, 2, 3]}"""
        ids = request.data.get('event_ids', [])
        updated = self.get_queryset().filter(
            id__in=ids,
            status=Event.Status.DRAFT,
        ).update(status=Event.Status.PUBLISHED)
        return Response({'published': updated})

    @action(detail=True, methods=['get'])
    def registrations(self, request, pk=None):
        """List all registrations for a specific event."""
        event = self.get_object()
        qs    = event.registrations.select_related('ticket_type').all()
        page  = self.paginate_queryset(qs)
        if page is not None:
            serializer = RegistrationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = RegistrationSerializer(qs, many=True)
        return Response(serializer.data)


class TicketTypeViewSet(TenantModelViewSet):
    serializer_class = TicketTypeSerializer
    queryset         = TicketType.objects.select_related('event').all()
    tenant_field     = 'event__organization'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsEventManager()]
        return super().get_permissions()

    def perform_create(self, serializer):
        event = serializer.validated_data.get('event')
        if not event:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'event': 'This field is required.'})
        if event.organization != self.request.tenant:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Event does not belong to this tenant.")
        serializer.save()


class RegistrationViewSet(TenantModelViewSet):
    serializer_class = RegistrationSerializer
    queryset         = Registration.objects.select_related('event', 'ticket_type').all()
    tenant_field     = 'event__organization'

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsEventManager()]
        return super().get_permissions()

    def perform_create(self, serializer):
        event = serializer.validated_data.get('event')
        if not event:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'event': 'This field is required.'})
        if event.organization != self.request.tenant:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Event does not belong to this tenant.")
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsEventManager])
    def confirm(self, request, pk=None):
        registration = self.get_object()
        registration.status = Registration.Status.CONFIRMED
        registration.save(update_fields=['status'])
        return Response({'status': 'confirmed'})

    @action(detail=True, methods=['post'], permission_classes=[IsEventManager])
    def cancel(self, request, pk=None):
        registration = self.get_object()
        registration.status = Registration.Status.CANCELLED
        registration.save(update_fields=['status'])
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'], permission_classes=[IsEventManager])
    def mark_attended(self, request, pk=None):
        registration = self.get_object()
        registration.status = Registration.Status.ATTENDED
        registration.save(update_fields=['status'])
        return Response({'status': 'attended'})