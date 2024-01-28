from django.contrib.auth.models import User
from django.db import models
import stripe
from choices import (
    CURRENCY_CHOICES,
    PAYMENT_METHOD_CHOICES,
    PAYMENT_STATUS_CHOICES,
)
from events.models import Event, TicketType, RSVP


class EventPaymentBill(models.Model):
    """Event Payment Bill for event organizers"""

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    currency = models.CharField(
        choices=CURRENCY_CHOICES, max_length=30, default=CURRENCY_CHOICES[1][1]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_event_bill_id = models.CharField(
        max_length=50, blank=True, null=True
    )
    has_finished_event = models.BooleanField(
        default=False, blank=True, null=True
    )
    has_completed_payment = models.BooleanField(
        default=False, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Event Payment Bill"
        verbose_name_plural = "Event Payment Bills"

    def __str__(self):
        return self.event.organizer.username + "-" + self.amount

    def save(self, *args, **kwargs):
        # Custom save logic here
        super().save(*args, **kwargs)

    def create_stripe_bill_for_organising_event(self):
        pass


class Transaction(models.Model):
    """The Transaction model for evnents and tickets"""

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    rsvp = models.OneToOneField(RSVP, on_delete=models.PROTECT, default=None)
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT)
    currency = models.CharField(
        choices=CURRENCY_CHOICES, max_length=30, default=CURRENCY_CHOICES[1][1]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(
        choices=PAYMENT_METHOD_CHOICES, max_length=30, blank=True, null=True
    )
    transaction_id = models.CharField(max_length=30, null=True, blank=True)
    payment_status = models.CharField(
        choices=PAYMENT_STATUS_CHOICES,
        max_length=30,
        default=None,
        blank=True,
        null=True,
    )
    billing_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return (
            self.user.username
            + "-"
            + self.ticket_type.name
            + "-"
            + self.ticket_type.event.name
        )

    def save(self, *args, **kwargs):
        # Custom save logic here
        super().save(*args, **kwargs)


class TransactionOfOrganizer(models.Model):
    """The Transaction model for organizer's events"""

    event_bill = models.OneToOneField(
        EventPaymentBill,
        on_delete=models.PROTECT,
        related_name="event_bill_transaction",
        default=None,
    )
    payment_date = models.DateTimeField()
    currency = models.CharField(
        choices=CURRENCY_CHOICES, max_length=30, default=CURRENCY_CHOICES[1][1]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(
        choices=PAYMENT_METHOD_CHOICES, max_length=30, blank=True, null=True
    )
    transaction_id = models.CharField(max_length=30, null=True, blank=True)
    payment_status = models.CharField(
        choices=PAYMENT_STATUS_CHOICES,
        max_length=30,
        default=None,
        blank=True,
        null=True,
    )
    billing_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Transaction of Organizer"
        verbose_name_plural = "Transactions of Organizer"

    def __str__(self):
        return self.event_bill.event.organizer.username + "-" + self.amount

    def save(self, *args, **kwargs):
        # Custom save logic here
        super().save(*args, **kwargs)
