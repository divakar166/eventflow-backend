# config/asgi.py
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings
from django.core.asgi import get_asgi_application

from apps.notifications.middleware import TenantWebsocketMiddleware
from apps.notifications.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

django_asgi_app = get_asgi_application()


if settings.DEBUG:
    # Skip origin validation in dev — *.localhost subdomains get rejected otherwise
    application = ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": TenantWebsocketMiddleware(URLRouter(websocket_urlpatterns)),
        }
    )
else:
    from channels.security.websocket import AllowedHostsOriginValidator

    application = ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": AllowedHostsOriginValidator(
                TenantWebsocketMiddleware(URLRouter(websocket_urlpatterns))
            ),
        }
    )
