from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from .permissions import IsTenantMember


class TenantModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that automatically scopes all queries and writes
    to the current request's tenant. Never returns cross-tenant data.

    Usage:
        class EventViewSet(TenantModelViewSet):
            serializer_class = EventSerializer
            queryset = Event.objects.all()   # will be auto-scoped
            tenant_field = 'organization'    # FK field name on your model
    """

    permission_classes = [IsTenantMember]
    tenant_field = 'organization'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(**{self.tenant_field: self.request.tenant})

    def perform_create(self, serializer):
        if '__' not in self.tenant_field:
            serializer.save(**{self.tenant_field: self.request.tenant})
        else:
            serializer.save()

    def perform_update(self, serializer):
        obj = self.get_object()
        if '__' not in self.tenant_field:
            if getattr(obj, self.tenant_field) != self.request.tenant:
                raise PermissionDenied("Object does not belong to this tenant.")
        serializer.save()

    def perform_destroy(self, instance):
        if '__' not in self.tenant_field:
            if getattr(instance, self.tenant_field) != self.request.tenant:
                raise PermissionDenied("Object does not belong to this tenant.")
        instance.delete()