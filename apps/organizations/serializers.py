from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import OrganizationUser

User = get_user_model()


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the default JWT serializer to embed the user's
    accessible organizations in the token payload.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        # Fetch all orgs this user belongs to
        memberships = OrganizationUser.objects.select_related('tenant').filter(
            user=self.user
        )

        organizations = [
            {
                'name': m.tenant.name,
                'slug': m.tenant.slug,
                'role': m.role,
                'domain': f"{m.tenant.slug}.localhost",
            }
            for m in memberships
        ]

        data['organizations'] = organizations
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'full_name': self.user.get_full_name(),
        }

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        return token


class OrganizationUserSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    tenant_slug = serializers.CharField(source='tenant.slug', read_only=True)

    class Meta:
        model = OrganizationUser
        fields = ['id', 'tenant_name', 'tenant_slug', 'role', 'joined_at']