from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import OrganizationUser, Tenant
from .serializers import TenantTokenObtainPairSerializer, OrganizationUserSerializer
from .permissions import IsTenantMember


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({
        'status': 'ok',
        'schema': connection.schema_name,
        'tenant': getattr(request.tenant, 'name', None),
        'tenant_slug': getattr(request.tenant, 'slug', None),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    Public domain  → returns basic user info only.
    Tenant subdomain → also returns role within that tenant.
    """
    data = {
        'id': request.user.id,
        'email': request.user.email,
        'full_name': request.user.get_full_name(),
    }
    
    tenant = getattr(request, 'tenant', None)
    is_real_tenant = (
        tenant is not None and
        getattr(tenant, 'schema_name', 'public') != 'public'
    )

    if is_real_tenant:
        try:
            membership = OrganizationUser.objects.select_related('tenant').get(
                user=request.user,
                tenant=tenant,
            )
            data['role'] = membership.role
            data['tenant'] = {
                'name': tenant.name,
                'slug': tenant.slug,
            }
        except OrganizationUser.DoesNotExist:
            return Response(
                {'detail': 'You are not a member of this organization.'},
                status=status.HTTP_403_FORBIDDEN,
            )

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_organizations(request):
    """
    Lists all orgs the current user belongs to.
    Always called on the public domain after login.
    Frontend uses this to build the org switcher / redirect.
    """
    memberships = OrganizationUser.objects.select_related('tenant').filter(
        user=request.user,
        tenant__is_active=True,
    )
    serializer = OrganizationUserSerializer(memberships, many=True)
    return Response(serializer.data)


class TenantTokenObtainPairView(TokenObtainPairView):
    serializer_class = TenantTokenObtainPairSerializer