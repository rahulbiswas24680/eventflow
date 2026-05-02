from celery import shared_task
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.db import transaction


@shared_task
def update_event_analytics(event_id: str):
    """
    Update analytics for a specific event.
    Called via signal on RSVP/Transaction creation.
    """
    from events.models import RSVP, Event
    from .models import EventAnalytics
    
    try:
        event = Event.objects.get(id=event_id)
        
        rsvps = RSVP.objects.filter(event=event, is_active=True, is_cancelled=False)
        
        total_rsvps = rsvps.count()
        total_revenue = rsvps.aggregate(
            total=Sum('total_charge')
        )['total'] or 0
        
        total_attended = rsvps.filter(is_attended=True).count()
        
        with transaction.atomic():
            analytics, created = EventAnalytics.objects.get_or_create(
                event=event,
                defaults={
                    'total_rsvps': total_rsvps,
                    'total_revenue': total_revenue,
                    'total_attended': total_attended,
                    'last_updated': timezone.now()
                }
            )
            
            if not created:
                analytics.total_rsvps = total_rsvps
                analytics.total_revenue = total_revenue
                analytics.total_attended = total_attended
                analytics.last_updated = timezone.now()
                analytics.save()
        
        return {
            'status': 'success',
            'event_id': event_id,
            'total_rsvps': total_rsvps,
            'total_revenue': float(total_revenue)
        }
        
    except Event.DoesNotExist:
        return {'status': 'failed', 'error': 'Event not found'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


@shared_task
def update_ticket_type_analytics(ticket_type_id: str):
    """
    Update analytics for a specific ticket type.
    Tracks sales and remaining capacity.
    """
    from events.models import TicketType, RSVP
    from .models import TicketTypeAnalytics
    
    try:
        ticket_type = TicketType.objects.get(id=ticket_type_id)
        
        rsvps = RSVP.objects.filter(
            transaction__ticket_type=ticket_type,
            is_active=True,
            is_cancelled=False
        )
        
        total_sold = rsvps.aggregate(
            total=Sum('ticket_qty')
        )['total'] or 0
        
        total_revenue = rsvps.aggregate(
            total=Sum('total_charge')
        )['total'] or 0
        
        remaining = ticket_type.quantity_available - total_sold
        
        with transaction.atomic():
            analytics, created = TicketTypeAnalytics.objects.get_or_create(
                ticket_type=ticket_type,
                defaults={
                    'total_sold': total_sold,
                    'total_revenue': total_revenue,
                    'remaining_quantity': remaining,
                    'last_updated': timezone.now()
                }
            )
            
            if not created:
                analytics.total_sold = total_sold
                analytics.total_revenue = total_revenue
                analytics.remaining_quantity = remaining
                analytics.last_updated = timezone.now()
                analytics.save()
        
        return {
            'status': 'success',
            'ticket_type_id': ticket_type_id,
            'total_sold': total_sold,
            'total_revenue': float(total_revenue)
        }
        
    except TicketType.DoesNotExist:
        return {'status': 'failed', 'error': 'TicketType not found'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


@shared_task
def refresh_all_analytics():
    """
    Full analytics refresh for all events.
    Run nightly or on-demand for data consistency.
    """
    from events.models import Event, TicketType
    
    events = Event.objects.all()
    ticket_types = TicketType.objects.all()
    
    event_count = 0
    for event in events:
        update_event_analytics.delay(str(event.id))
        event_count += 1
    
    ticket_count = 0
    for ticket_type in ticket_types:
        update_ticket_type_analytics.delay(str(ticket_type.id))
        ticket_count += 1
    
    return {
        'status': 'queued',
        'events_queued': event_count,
        'ticket_types_queued': ticket_count
    }


@shared_task
def daily_analytics_summary():
    """
    Generate daily summary of platform analytics.
    Run via Celery Beat at midnight for dashboard updates.
    """
    from events.models import Event, RSVP
    from payments.models import Transaction
    
    today = timezone.now().date()
    
    new_events = Event.objects.filter(created_at__date=today).count()
    new_rsvps = RSVP.objects.filter(created_at__date=today).count()
    new_transactions = Transaction.objects.filter(
        created_at__date=today,
        payment_status='SUCCESS'
    ).count()
    
    total_revenue_today = Transaction.objects.filter(
        created_at__date=today,
        payment_status='SUCCESS'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    return {
        'date': str(today),
        'new_events': new_events,
        'new_rsvps': new_rsvps,
        'new_transactions': new_transactions,
        'revenue': float(total_revenue_today)
    }