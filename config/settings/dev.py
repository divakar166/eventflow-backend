from .base import *

DEBUG = True

INSTALLED_APPS += ['debug_toolbar']

MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

INTERNAL_IPS = ['127.0.0.1']
ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'