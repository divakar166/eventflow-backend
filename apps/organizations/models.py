from django.db import models
from django.contrib.auth import get_user_model
from django_tenants.models import TenantMixin, DomainMixin


class Tenant(TenantMixin):
    """
    One row per organization in the PUBLIC schema.
    django-tenants uses this to switch the DB search_path.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # Automatically create a schema when a tenant is saved
    auto_create_schema = True

    class Meta:
        app_label = 'organizations'

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    """
    Maps a hostname like acme.localhost → Tenant.
    One tenant can have multiple domains.
    """
    class Meta:
        app_label = 'organizations'


class OrganizationUser(models.Model):
    """
    Links a Django User to a Tenant with a role.
    Lives in the PUBLIC schema (shared app).
    """
    class Role(models.TextChoices):
        ADMIN   = 'admin',   'Org Admin'
        MANAGER = 'manager', 'Event Manager'
        VIEWER  = 'viewer',  'Viewer'

    user   = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='organization_memberships'
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='members'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'organizations'
        unique_together = ('user', 'tenant')

    def __str__(self):
        return f"{self.user.email} @ {self.tenant.name} ({self.role})"