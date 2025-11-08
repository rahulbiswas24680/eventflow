
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

    def __str__(self):
        return self.name + '-' + self.event.name


    def save(self, *args, **kwargs):
        if not self.stripe_price_id:
            product_price = self.create_stripe_ticket_as_prod()
            self.stripe_price_id = product_price.id

        super().save(*args, **kwargs)

    def create_stripe_ticket_as_prod(self):
        prod = stripe.Product.create(
            name=self.name,
            description=f'The ticket of {self.event.name} event.',
            active=True
        )
        prod_price = stripe.Price.create(
            product=prod.id,
            currency='inr',
            unit_amount=int(self.price * 100)
        )

        return prod_price


class RSVP(models.Model):
    transaction_id = models.CharField(max_length=30, default=None)
    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    attendee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    ticket_qty = models.PositiveIntegerField(default=1)
    total_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=False)
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

    def __str__(self):
        return self.attendee.id.__str__() + '-' + self.event.name

    def save(self, *args, **kwargs):
        # Decrement ticket quantity when RSVP is completed
        if self.is_completed and not self.pk:
            # Only decrement on new completed RSVPs
            ticket_type = self.event.tickettype_set.first()
            if ticket_type and ticket_type.quantity_available >= self.ticket_qty:
                ticket_type.quantity_available -= self.ticket_qty
                ticket_type.save()
            else:
                raise ValueError("Not enough tickets available")
        super().save(*args, **kwargs)
