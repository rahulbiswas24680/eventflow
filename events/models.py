
import stripe
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from rsvp.storage import SupabaseStorage

s = SupabaseStorage()


class Event(models.Model):
    organizer = models.ForeignKey(User, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateTimeField()
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Event'
        verbose_name_plural = 'Events'

    def __str__(self):
        return self.name + '-' + self.organizer.first_name

    def save(self, *args, **kwargs):
        # Custom save logic here
        super().save(*args, **kwargs)


class EventImage(models.Model):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='event_img/')

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

    def clean(self):
        if s.exists(f"ticket_img/{self.image}"):
            raise ValidationError('Image already uploaded. Try different one.')
        super(TicketType, self).clean()

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
            unit_amount=int(self.price)
        )

        return prod_price


class RSVP(models.Model):
    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    attendee = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    # need to link it with event payment transaction details model

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'RSVP'
        verbose_name_plural = 'RSVPs'

    def __str__(self):
        return self.attendee.first_name + '-' + self.event.name

    def save(self, *args, **kwargs):
        # Custom save logic here
        super().save(*args, **kwargs)
