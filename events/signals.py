from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Event
from payments.models import EventPaymentBill

@receiver(post_save, sender=Event)
def create_event_payment_bill(sender, instance, created, **kwargs):
    """
    Automatically create an EventPaymentBill when an event is marked as finished.
    """
    # Check if the event has just been marked as finished
    if hasattr(instance, '_original_has_finished_event'):
        if not instance._original_has_finished_event and instance.has_finished_event:
            # Event has just been marked as finished, create payment bill
            EventPaymentBill.objects.get_or_create(
                event=instance,
                organizer=instance.organizer,
                defaults={
                    'amount': 0,  # This should be calculated based on ticket sales
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
