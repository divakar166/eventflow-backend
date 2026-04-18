from rest_framework.permissions import BasePermission
from .models import OrganizationUser


class IsTenantMember(BasePermission):
    """Request user must be a member of the current tenant."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return OrganizationUser.objects.filter(
            user=request.user,
            tenant=request.tenant,
        ).exists()


class IsOrgAdmin(BasePermission):
    """Request user must have the admin role in the current tenant."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return OrganizationUser.objects.filter(
            user=request.user,
            tenant=request.tenant,
            role=OrganizationUser.Role.ADMIN,
        ).exists()


class IsEventManager(BasePermission):
    """Admin or Event Manager role."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return OrganizationUser.objects.filter(
            user=request.user,
            tenant=request.tenant,
            role__in=[OrganizationUser.Role.ADMIN, OrganizationUser.Role.MANAGER],
        ).exists()