from celery import shared_task
from django.conf import settings
from django.db import transaction

from events.models import RSVP
from qr_codes.models import QRCode
from .models import Transaction


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True
)
def process_checkout_session(self, session_id: str):
    """
    Process completed Stripe checkout session asynchronously.
    Handles RSVP creation, QR code generation, and email notification.
    
    Features:
    - Idempotency: Checks if already processed before running
    - Retry with exponential backoff on failure
    - Transaction-level atomicity for data consistency
    """
    try:
        with transaction.atomic():
            transactions = Transaction.objects.select_related(
                'ticket_type__event',
                'user',
                'rsvp'
            ).filter(session_id=session_id, payment_status='PENDING')
            
            if not transactions.exists():
                return {'status': 'already_processed', 'session_id': session_id}
            
            payment_intent = None
            processed_count = 0
            
            for txn in transactions:
                txn.payment_status = 'SUCCESS'
                payment_intent = txn.transaction_id
                
                ticket_obj = txn.ticket_type
                user = txn.user
                
                rsvp_obj = RSVP.objects.create(
                    event=ticket_obj.event,
                    attendee=user,
                    transaction_id=txn.transaction_id,
                    ticket_qty=txn.quantity,
                    total_charge=txn.amount * txn.quantity,
                    is_active=True,
                    metadata={}
                )
                
                txn.rsvp = rsvp_obj
                txn.save(update_fields=['payment_status', 'transaction_id', 'rsvp'])
                
                from qr_codes.tasks import generate_qr_code
                generate_qr_code.delay(str(txn.id))
                
                from communication.tasks.mail_tasks import ticket_payment_user_mail
                ticket_payment_user_mail.delay(
                    user_name=user.first_name or user.email.split('@')[0],
                    recipients=[user.email]
                )
                
                processed_count += 1
            
            return {
                'status': 'success',
                'session_id': session_id,
                'processed': processed_count
            }
            
    except Exception as e:
        raise self.retry(exc=e)


@shared_task
def refund_transaction(transaction_id: str):
    """
    Process refund for a transaction via Stripe API.
    Called when organizer requests refund or automatic refund triggers.
    """
    import stripe
    from decouple import config
    
    stripe.api_key = config("STRIPE_SECRET_KEY")
    
    try:
        with transaction.atomic():
            txn = Transaction.objects.select_related('rsvp').get(id=transaction_id)
            
            if txn.payment_status != 'SUCCESS':
                return {'status': 'failed', 'reason': 'Transaction not successful'}
            
            if txn.transaction_id:
                stripe.Refund.create(payment_intent=txn.transaction_id)
            
            txn.payment_status = 'REFUNDED'
            txn.save(update_fields=['payment_status'])
            
            if txn.rsvp:
                txn.rsvp.is_cancelled = True
                txn.rsvp.is_active = False
                txn.rsvp.save(update_fields=['is_cancelled', 'is_active'])
            
            return {'status': 'success', 'transaction_id': transaction_id}
            
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}