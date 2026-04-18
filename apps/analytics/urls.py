from django.urls import path
from . import views

urlpatterns = [
    path('analytics/summary/',                views.summary,                 name='analytics-summary'),
    path('analytics/registrations-over-time/', views.registrations_over_time, name='analytics-reg-time'),
    path('analytics/revenue-over-time/',       views.revenue_over_time,       name='analytics-rev-time'),
    path('analytics/top-events/',              views.top_events,              name='analytics-top-events'),
    path('analytics/ticket-breakdown/',        views.ticket_type_breakdown,   name='analytics-ticket-breakdown'),
    path('analytics/invalidate-cache/',        views.invalidate_cache,        name='analytics-invalidate-cache'),
]