import io
from celery import shared_task
from apps.organizations.tasks import tenant_task


@shared_task(bind=True, max_retries=3)
@tenant_task
def generate_qr_code(self, schema_name, registration_id):
    """Generate QR code image and save to Registration.qr_code field."""
    import qrcode
    from django.core.files.base import ContentFile
    from .models import Registration

    try:
        registration = Registration.objects.get(id=registration_id)
    except Registration.DoesNotExist:
        return f"Registration {registration_id} not found."

    # QR data: encode registration ID + email for check-in validation
    qr_data = f"EVENTFLOW:{registration.id}:{registration.attendee_email}"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    filename = f"qr_{registration_id}.png"
    registration.qr_code.save(filename, ContentFile(buffer.read()), save=True)

    return f"QR code saved for registration {registration_id}."