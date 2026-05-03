from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import stripe
from decouple import config


@shared_task(
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=120,
    soft_time_limit=90
)
def generate_ticket_pdf(self, rsvp_id: str):
    """
    Generate PDF ticket asynchronously for an RSVP.
    
    Frontend can poll for task status and get download URL when ready.
    Heavy operation moved out of HTTP request cycle.
    """
    from .models import RSVP
    from weasyprint import HTML
    from django.template.loader import render_to_string
    import os
    import uuid
    
    try:
        rsvp = RSVP.objects.select_related(
            'event__organizer__user',
            'attendee',
            'transaction__ticket_type'
        ).get(id=rsvp_id)
        
        context = {
            'rsvp': rsvp,
            'event': rsvp.event,
            'ticket_type': rsvp.transaction.ticket_type,
            'attendee': rsvp.attendee,
            'site_url': settings.SITE_URL,
        }
        
        html_string = render_to_string('events/ticket_pdf.html', context)
        
        pdf_file = HTML(string=html_string).write_pdf()
        
        from django.core.files import File
        from django.core.files.temp import NamedTemporaryFile
        
        temp_file = NamedTemporaryFile(delete=True)
        temp_file.write(pdf_file)
        temp_file.flush()
        
        filename = f'ticket_{rsvp.id}_{uuid.uuid4().hex[:8]}.pdf'
        
        from django.conf import settings
        from django.core.files.storage import default_storage
        
        pdf_path = f'tickets/{filename}'
        saved_path = default_storage.save(pdf_path, File(temp_file))
        
        full_url = f"{settings.SITE_URL}/media/{saved_path}"
        
        return {
            'status': 'success',
            'rsvp_id': rsvp_id,
            'pdf_url': full_url
        }
        
    except RSVP.DoesNotExist:
        return {'status': 'failed', 'error': 'RSVP not found'}
    except Exception as e:
        raise self.retry(exc=e, max_retries=2)


@shared_task
def mark_finished_events():
    """
    Periodic task to mark events that have ended as finished.
    Runs hourly via Celery Beat.
    """
    from .models import Event
    
    now = timezone.now()
    
    finished_events = Event.objects.filter(
        date__lt=now.date(),
        has_finished_event=False
    )
    
    count = finished_events.update(has_finished_event=True)
    
    return {'status': 'success', 'events_updated': count}


@shared_task
def send_event_reminders():
    """
    Send reminder emails to attendees 24 hours before event starts.
    Runs daily via Celery Beat at 9 AM.
    """
    from .models import RSVP
    
    now = timezone.now()
    from datetime import timedelta
    
    tomorrow = now + timedelta(days=1)
    tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0)
    tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59)
    
    upcoming_rsvps = RSVP.objects.filter(
        event__date=tomorrow.date(),
        is_active=True,
        is_cancelled=False
    ).select_related('event', 'attendee')
    
    from communication.tasks.mail_tasks import ongoing_events_mail
    
    sent_count = 0
    for rsvp in upcoming_rsvps:
        if rsvp.attendee.email:
            ongoing_events_mail.delay(
                user_name=rsvp.attendee.first_name or rsvp.attendee.email.split('@')[0],
                recipients=[rsvp.attendee.email]
            )
            sent_count += 1
    
    return {'status': 'success', 'reminders_sent': sent_count}


@shared_task
def bulk_generate_tickets(rsvp_ids: list):
    """
    Generate PDFs for multiple RSVPs in bulk.
    Useful when regenerating tickets after event updates.
    """
    import uuid
    from .models import RSVP
    
    rsvps = RSVP.objects.filter(id__in=rsvp_ids).select_related(
        'event__organizer__user',
        'attendee',
        'transaction__ticket_type'
    )
    
    from weasyprint import HTML
    from django.template.loader import render_to_string
    from django.core.files import File
    from django.core.files.temp import NamedTemporaryFile
    from django.core.files.storage import default_storage
    
    success_count = 0
    generated_files = []
    
    for rsvp in rsvps:
        try:
            context = {
                'rsvp': rsvp,
                'event': rsvp.event,
                'ticket_type': rsvp.transaction.ticket_type,
                'attendee': rsvp.attendee,
                'site_url': settings.SITE_URL,
            }
            
            html_string = render_to_string('events/ticket_pdf.html', context)
            pdf_file = HTML(string=html_string).write_pdf()
            
            temp_file = NamedTemporaryFile(delete=True)
            temp_file.write(pdf_file)
            temp_file.flush()
            
            filename = f'ticket_{rsvp.id}_{uuid.uuid4().hex[:8]}.pdf'
            pdf_path = f'tickets/{filename}'
            saved_path = default_storage.save(pdf_path, File(temp_file))
            
            generated_files.append({
                'rsvp_id': str(rsvp.id),
                'pdf_url': f"{settings.SITE_URL}/media/{saved_path}"
            })
            success_count += 1
            
        except Exception:
            continue
    
    return {
        'status': 'completed',
        'total': len(rsvp_ids),
        'success': success_count,
        'files': generated_files
    }


@shared_task(
    bind=True,
    autoretry_for=(stripe.error.APIError,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True
)
def create_stripe_product_for_ticket(self, ticket_type_id: str):
    """
    Create Stripe Product and Price asynchronously for a TicketType.
    Called via signal when ticket type is created or updated.
    """
    from .models import TicketType
    
    stripe.api_key = config("STRIPE_SECRET_KEY")
    
    try:
        ticket_type = TicketType.objects.select_related('event').get(id=ticket_type_id)
        
        if ticket_type.stripe_price_id:
            return {'status': 'skipped', 'reason': 'already_has_stripe_price_id'}
        
        product = stripe.Product.create(
            name=ticket_type.name,
            description=f'The ticket of {ticket_type.event.name} event.',
            active=True
        )
        
        price = stripe.Price.create(
            product=product.id,
            currency='inr',
            unit_amount=int(ticket_type.price * 100)
        )
        
        ticket_type.stripe_price_id = price.id
        ticket_type.save(update_fields=['stripe_price_id'])
        
        return {
            'status': 'success',
            'ticket_type_id': ticket_type_id,
            'stripe_price_id': price.id
        }
        
    except TicketType.DoesNotExist:
        return {'status': 'failed', 'error': 'TicketType not found'}
    except Exception as e:
        raise self.retry(exc=e)


@shared_task
def create_stripe_products_bulk(ticket_type_ids: list):
    """
    Create Stripe products for multiple ticket types in bulk.
    Useful when migrating existing tickets to Stripe.
    """
    from .models import TicketType
    
    stripe.api_key = config("STRIPE_SECRET_KEY")
    
    ticket_types = TicketType.objects.filter(
        id__in=ticket_type_ids,
        stripe_price_id__isnull=True
    ).select_related('event')
    
    success_count = 0
    results = []
    
    for ticket_type in ticket_types:
        try:
            product = stripe.Product.create(
                name=ticket_type.name,
                description=f'The ticket of {ticket_type.event.name} event.',
                active=True
            )
            
            price = stripe.Price.create(
                product=product.id,
                currency='inr',
                unit_amount=int(ticket_type.price * 100)
            )
            
            ticket_type.stripe_price_id = price.id
            ticket_type.save(update_fields=['stripe_price_id'])
            
            results.append({
                'ticket_type_id': str(ticket_type.id),
                'status': 'success',
                'stripe_price_id': price.id
            })
            success_count += 1
            
        except Exception as e:
            results.append({
                'ticket_type_id': str(ticket_type.id),
                'status': 'failed',
                'error': str(e)
            })
    
    return {
        'status': 'completed',
        'total': len(ticket_type_ids),
        'success': success_count,
        'results': results
    }


@shared_task
def refresh_currency_rates():
    """
    Refresh forex rates in cache daily.
    Run via Celery Beat every 24 hours.
    """
    from forex_python.converter import CurrencyRates
    from django.core.cache import cache
    
    base_currency = "INR"
    target_currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]
    
    c = CurrencyRates()
    results = {}
    
    for currency in target_currencies:
        try:
            rate = c.get_rate(currency, base_currency)
            cache_key = f"forex_rate:{currency}:{base_currency}"
            cache.set(cache_key, rate, timeout=86400 * 2)
            results[currency] = rate
        except Exception as e:
            results[currency] = f"error: {str(e)}"
    
    return {'status': 'success', 'rates': results}