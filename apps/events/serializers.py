from rest_framework import serializers
from .models import Event, TicketType, Registration


class TicketTypeSerializer(serializers.ModelSerializer):
    available_quantity = serializers.ReadOnlyField()

    class Meta:
        model  = TicketType
        fields = [
            'id', 'name', 'event', 'description', 'price',
            'quantity', 'available_quantity',
            'promo_code', 'promo_price', 'is_active',
        ]
        extra_kwargs = {
            'promo_code': {'write_only': True},
            'event': {'write_only': False},
        }


class EventSerializer(serializers.ModelSerializer):
    ticket_types = TicketTypeSerializer(many=True, read_only=True)
    is_sold_out  = serializers.ReadOnlyField()
    organization = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = Event
        fields = [
            'id', 'name', 'description', 'venue',
            'start_datetime', 'end_datetime', 'capacity',
            'status', 'is_recurring', 'recurrence_rule',
            'is_sold_out', 'organization', 'ticket_types',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['organization', 'created_at', 'updated_at']

    def validate(self, data):
        if data.get('end_datetime') and data.get('start_datetime'):
            if data['end_datetime'] <= data['start_datetime']:
                raise serializers.ValidationError(
                    {'end_datetime': 'End datetime must be after start datetime.'}
                )
        return data


class RegistrationSerializer(serializers.ModelSerializer):
    event_name      = serializers.CharField(source='event.name', read_only=True)
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)

    class Meta:
        model  = Registration
        fields = [
            'id', 'event', 'event_name',
            'ticket_type', 'ticket_type_name',
            'attendee_name', 'attendee_email', 'attendee_phone',
            'status', 'notes', 'registered_at',
        ]
        read_only_fields = ['id', 'status', 'registered_at']

    def validate(self, data):
        ticket_type = data.get('ticket_type')
        event       = data.get('event')

        # Ticket type must belong to the event
        if ticket_type and event and ticket_type.event_id != event.id:
            raise serializers.ValidationError(
                {'ticket_type': 'This ticket type does not belong to the selected event.'}
            )

        # Check availability
        if ticket_type and ticket_type.available_quantity == 0:
            raise serializers.ValidationError(
                {'ticket_type': 'This ticket type is sold out.'}
            )

        # Check event capacity
        if event and event.is_sold_out:
            raise serializers.ValidationError(
                {'event': 'This event is sold out.'}
            )

        return data