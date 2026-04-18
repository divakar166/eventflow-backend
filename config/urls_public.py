from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from apps.organizations.views import my_organizations, TenantTokenObtainPairView, me
from apps.payments.views import stripe_webhook
from rest_framework_simplejwt.views import TokenRefreshView


def public_health(request):
    return JsonResponse({'status': 'ok', 'schema': 'public'})


urlpatterns = [
    path('health/', public_health),
    path('api/v1/auth/login/', TenantTokenObtainPairView.as_view()),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view()),
    path('api/v1/my-organizations/', my_organizations),
    path('api/v1/me/', me),
    path('api/v1/webhooks/stripe/', stripe_webhook),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]