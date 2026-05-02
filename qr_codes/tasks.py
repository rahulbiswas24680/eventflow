import random
import string
from io import BytesIO

import segno
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=60,
    soft_time_limit=45
)
def generate_qr_code(self, transaction_id: str):
    """
    Generate QR code asynchronously for a transaction.
    
    Moved out of QRCode.save() to prevent blocking HTTP requests.
    Can be chained after payment processing for seamless flow.
    """
    from .models import QRCode
    from payments.models import Transaction
    
    try:
        transaction = Transaction.objects.select_related('rsvp').get(id=transaction_id)
        
        qr_code, created = QRCode.objects.get_or_create(transaction=transaction)
        
        ticket_url = f"{settings.SITE_URL}/ticket/{transaction.rsvp.id}/"
        qr_code.code_data = ticket_url
        
        qr_data = str(ticket_url)
        qr_image = segno.make(
            qr_data,
            micro=False,
            error='h',
        )
        
        fname = "".join(random.choice(string.ascii_lowercase) for _ in range(8)) + ".png"
        
        img_buffer = BytesIO()
        qr_image.save(
            img_buffer,
            kind="png",
            scale=10,
            border=2,
            dark="#2D3748",
            light="#F7FAFC",
            data_dark="#425239",
        )
        img_buffer.seek(0)
        
        qr_code.code_image.save(fname, ContentFile(img_buffer.read()), save=True)
        
        return {
            'status': 'success',
            'qr_code_id': str(qr_code.id),
            'transaction_id': transaction_id
        }
        
    except Transaction.DoesNotExist:
        return {'status': 'failed', 'error': 'Transaction not found'}
    except Exception as e:
        raise self.retry(exc=e, max_retries=3)


@shared_task
def regenerate_qr_code(qr_code_id: str):
    """
    Regenerate QR code for existing QRCode record.
    Useful for fixing corrupted images or changing QR format.
    """
    from .models import QRCode
    
    try:
        qr_code = QRCode.objects.select_related('transaction__rsvp').get(id=qr_code_id)
        
        if qr_code.transaction and qr_code.transaction.rsvp:
            ticket_url = f"{settings.SITE_URL}/ticket/{qr_code.transaction.rsvp.id}/"
            qr_code.code_data = ticket_url
        else:
            qr_code.code_data = f"{settings.SITE_URL}/invalid-ticket"
        
        qr_data = str(qr_code.code_data)
        qr_image = segno.make(qr_data, micro=False, error='h')
        
        fname = "".join(random.choice(string.ascii_lowercase) for _ in range(8)) + ".png"
        
        img_buffer = BytesIO()
        qr_image.save(
            img_buffer,
            kind="png",
            scale=10,
            border=2,
            dark="#2D3748",
            light="#F7FAFC",
        )
        img_buffer.seek(0)
        
        qr_code.code_image.save(fname, ContentFile(img_buffer.read()), save=True)
        
        return {'status': 'success', 'qr_code_id': qr_code_id}
        
    except QRCode.DoesNotExist:
        return {'status': 'failed', 'error': 'QRCode not found'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}