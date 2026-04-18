from urllib.parse import urlparse
from channels.db import database_sync_to_async
from django.db import connection


class TenantWebsocketMiddleware:
    """
    Resolves the tenant from the WebSocket request's Host header
    and sets the DB schema before the consumer runs.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            scope = await self._set_tenant(scope)
        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def _set_tenant(self, scope):
        from apps.organizations.models import Domain

        headers = dict(scope.get('headers', []))
        host    = headers.get(b'host', b'').decode().split(':')[0]

        try:
            domain = Domain.objects.select_related('tenant').get(domain=host)
            tenant = domain.tenant
            connection.set_schema(tenant.schema_name)
            scope['tenant'] = tenant
        except Domain.DoesNotExist:
            scope['tenant'] = None

        return scope