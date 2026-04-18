from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('events',        views.EventViewSet,        basename='event')
router.register('ticket-types',  views.TicketTypeViewSet,   basename='ticket-type')
router.register('registrations', views.RegistrationViewSet, basename='registration')

urlpatterns = [
    path('', include(router.urls)),
]