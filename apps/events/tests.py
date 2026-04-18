# apps/events/tests.py
import pytest
from django_tenants.test.cases import FastTenantTestCase
from django_tenants.test.client import TenantClient
from django.contrib.auth import get_user_model
from apps.organizations.models import Tenant, Domain, OrganizationUser
from apps.events.models import Event
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class EventAPITestCase(FastTenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.name = 'Test Org'
        tenant.slug = 'test'
        return tenant

    def setUp(self):
        self.client = TenantClient(self.tenant)
        self.user   = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        OrganizationUser.objects.create(
            user=self.user,
            tenant=self.tenant,
            role=OrganizationUser.Role.ADMIN,
        )
        self.client.force_login(self.user)

    def test_create_event(self):
        response = self.client.post('/api/v1/events/', {
            'name'           : 'Test Event',
            'venue'          : 'Bangalore',
            'start_datetime' : (timezone.now() + timedelta(days=1)).isoformat(),
            'end_datetime'   : (timezone.now() + timedelta(days=1, hours=2)).isoformat(),
            'capacity'       : 100,
        }, content_type='application/json')
        assert response.status_code == 201
        assert response.json()['name'] == 'Test Event'

    def test_event_scoped_to_tenant(self):
        """Events created in one tenant must not appear in another."""
        Event.objects.create(
            organization=self.tenant,
            name='Acme Event',
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now()   + timedelta(days=1, hours=2),
        )
        response = self.client.get('/api/v1/events/')
        assert response.status_code == 200
        # Only this tenant's events returned
        for event in response.json()['results']:
            assert event['organization'] == self.tenant.name

    def test_cross_tenant_leak(self):
        """The critical test — verify no cross-tenant data leaks."""
        # Create a second tenant
        other = Tenant(schema_name='other', name='Other Org', slug='other')
        other.save()
        Domain.objects.create(domain='other.localhost', tenant=other, is_primary=True)

        # Create event in other tenant's schema
        from django_tenants.utils import tenant_context
        with tenant_context(other):
            Event.objects.create(
                organization=other,
                name='Other Tenant Event',
                start_datetime=timezone.now() + timedelta(days=1),
                end_datetime=timezone.now()   + timedelta(days=1, hours=2),
            )

        # Current tenant must not see other tenant's event
        response = self.client.get('/api/v1/events/')
        names = [e['name'] for e in response.json()['results']]
        assert 'Other Tenant Event' not in names