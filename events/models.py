
import os
from decimal import Decimal

import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# from rsvp.storage import SupabaseStorage

# s = SupabaseStorage()


class Event(models.Model):
    organizer = models.ForeignKey('user_profiles.Organizer', on_delete=models.PROTECT, default=None)
    name = models.CharField(max_length=255)
    description = models.TextField()
    description_html = models.TextField(blank=True, null=True)
    date = models.DateTimeField()
    location = models.TextField(blank=True, null=True)
    metadata = models.JSONField(null=True, blank=True)
    is_virtual = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    has_finished_event = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        indexes = [
            models.Index(fields=['date'], name='event_date_idx'),
            models.Index(fields=['is_published', 'is_active', 'date'], name='event_pub_act_date_idx'),
            models.Index(fields=['has_finished_event', 'date'], name='event_finish_date_idx'),
            models.Index(fields=['organizer', '-created_at'], name='event_org_created_idx'),
        ]

    def __str__(self):
        return self.name + '-' + self.organizer.organizer_name

    def save(self, *args, **kwargs):
        # Store original has_finished_event status before saving
        if self.pk:
            from django.db import transaction
            old_instance = Event.objects.get(pk=self.pk)
            self._original_has_finished_event = old_instance.has_finished_event
        else:
            self._original_has_finished_event = False
        super().save(*args, **kwargs)

    @property
    def first_image(self):
        return self.images.first()


class EventImage(models.Model):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='event_img/%Y/%m/%d/')

    def __str__(self):
        return self.event.name + ' - Image'


class CurrencyAwareDecimalField(models.DecimalField):
    """
    Custom model field for handling currency conversion.
    """

    def __init__(self, *args, **kwargs):
        self.currency_field = kwargs.pop('currency_field', None)
        super().__init__(*args, **kwargs)


class TicketType(models.Model):

    from choices import CURRENCY_CHOICES

    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(
        choices=CURRENCY_CHOICES, max_length=10, default=CURRENCY_CHOICES[1][1])
    image = models.ImageField(
        upload_to='ticket_img/', blank=True, null=True,
        editable=True, default=None)
    stripe_price_id = models.CharField(max_length=50, blank=True, null=True)
    quantity_available = models.PositiveIntegerField()
    discount_code = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'TicketType'
        verbose_name_plural = 'TicketTypes'
        indexes = [
            models.Index(fields=['event', '-created_at'], name='tickettype_event_idx'),
            models.Index(fields=['stripe_price_id'], name='tickettype_stripe_idx'),
        ]

    def __str__(self):
        return self.name + '-' + self.event.name


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class RSVP(models.Model):
    transaction_id = models.CharField(max_length=30, default=None)
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='attendees')
    attendee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    ticket_qty = models.PositiveIntegerField(default=1)
    total_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=False)
    is_attended = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    is_refunded = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'RSVP'
        verbose_name_plural = 'RSVPs'
        indexes = [
            models.Index(fields=['event', '-created_at'], name='rsvp_event_idx'),
            models.Index(fields=['attendee', '-created_at'], name='rsvp_attendee_idx'),
            models.Index(fields=['transaction_id'], name='rsvp_txn_id_idx'),
            models.Index(fields=['is_active', 'is_cancelled', 'is_attended'], name='rsvp_status_idx'),
            models.Index(fields=['event', 'is_active'], name='rsvp_event_active_idx'),
        ]

    def __str__(self):
        return self.attendee.id.__str__() + '-' + self.event.name

    def save(self, *args, **kwargs):
        # Auto-set is_completed based on other statuses
        if self.is_attended and not self.is_cancelled:
            self.is_completed = True
        elif self.is_cancelled:
            self.is_completed = False
            
        # Auto-set is_active
        self.is_active = not (self.is_cancelled or self.is_completed or self.is_expired)
        
        # Handle ticket quantity when RSVP is completed - with race condition protection
        if self.is_completed and not self.pk:
            from django.db import transaction
            with transaction.atomic():
                # Lock the ticket type row to prevent over-selling
                ticket_type = self.event.tickettype_set.select_for_update().first()
                if ticket_type and ticket_type.quantity_available >= self.ticket_qty:
                    ticket_type.quantity_available -= self.ticket_qty
                    ticket_type.save(update_fields=['quantity_available'])
                else:
                    raise ValueError("Not enough tickets available")
                
        super().save(*args, **kwargs)

    @property
    def status(self):
        if self.is_cancelled:
            return "cancelled"
        elif self.is_attended:
            return "attended"
        elif self.is_completed:
            return "completed"
        else:
            return "registered"