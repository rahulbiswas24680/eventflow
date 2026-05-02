from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import Event, RSVP, TicketType
from payments.models import EventPaymentBill


@receiver(post_save, sender=Event)
def create_event_payment_bill(sender, instance, created, **kwargs):
    """
    Automatically create an EventPaymentBill when an event is marked as finished.
    """
    if hasattr(instance, '_original_has_finished_event'):
        if not instance._original_has_finished_event and instance.has_finished_event:
            EventPaymentBill.objects.get_or_create(
                event=instance,
                organizer=instance.organizer,
                defaults={
                    'amount': 0,
                    'has_finished_event': True,
                }
            )


@receiver(post_save, sender=Event)
def track_event_finish_status(sender, instance, **kwargs):
    """
    Store the original has_finished_event status to detect changes.
    """
    if not hasattr(instance, '_original_has_finished_event'):
        instance._original_has_finished_event = instance.has_finished_event


@receiver(post_save, sender=RSVP)
def trigger_analytics_update_on_rsvp(sender, instance, created, **kwargs):
    """
    Trigger analytics update when RSVP is created or updated.
    Uses Celery for async processing to avoid blocking the save operation.
    """
    if created or instance.is_active:
        try:
            from analytics.tasks import update_event_analytics
            transaction.on_commit(lambda: 
                update_event_analytics.delay(str(instance.event_id))
            )
        except Exception:
            pass


@receiver(post_save, sender=RSVP)
def trigger_ticket_analytics_update(sender, instance, created, **kwargs):
    """
    Trigger ticket type analytics when RSVP is created.
    """
    if created and instance.transaction_id:
        try:
            from analytics.tasks import update_ticket_type_analytics
            transaction.on_commit(lambda:
                update_ticket_type_analytics.delay(str(instance.transaction.ticket_type_id))
            )
        except Exception:
            pass


@receiver(pre_save, sender=TicketType)
def store_original_stripe_price(sender, instance, **kwargs):
    """
    Store original stripe_price_id to detect changes.
    """
    if instance.pk:
        try:
            instance._original_stripe_price_id = TicketType.objects.get(pk=instance.pk).stripe_price_id
        except TicketType.DoesNotExist:
            instance._original_stripe_price_id = None
    else:
        instance._original_stripe_price_id = None


@receiver(post_save, sender=TicketType)
def trigger_stripe_product_creation(sender, instance, created, **kwargs):
    """
    Trigger async Stripe Product/Price creation when TicketType is created or price changes.
    """
    original_price_id = getattr(instance, '_original_stripe_price_id', None)
    
    should_create = (
        (created and not instance.stripe_price_id) or
        (not created and instance.stripe_price_id != original_price_id and instance.price)
    )
    
    if should_create:
        try:
            from .tasks import create_stripe_product_for_ticket
            transaction.on_commit(lambda:
                create_stripe_product_for_ticket.delay(str(instance.id))
            )
        except Exception:
            pass
