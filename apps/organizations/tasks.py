import functools
from celery import shared_task
from django_tenants.utils import schema_context

def tenant_task(func):
    """
    Decorator that makes a Celery task schema-aware.
    Usage:
        @shared_task
        @tenant_task
        def my_task(schema_name, ...):
            # DB queries here are scoped to schema_name
    
    Always pass schema_name as the first argument when calling:
        my_task.delay(tenant.schema_name, other_args)
    """
    @functools.wraps(func)
    def wrapper(schema_name, *args, **kwargs):
        with schema_context(schema_name):
            return func(schema_name, *args, **kwargs)
    return wrapper