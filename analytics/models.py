
from django.db import models
from events.models import Event, TicketType


class EventAnalytics(models.Model):
    event = models.OneToOneField(Event, on_delete=models.PROTECT)
    total_rsvps = models.IntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    total_attended = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'EventAnalytics'
        indexes = [
            models.Index(fields=['event'], name='analytics_event_idx'),
        ]

    def __str__(self):
        return self.event.name


class TicketTypeAnalytics(models.Model):
    ticket_type = models.OneToOneField(TicketType, on_delete=models.PROTECT)
    total_sold = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'TicketTypeAnalytics'
        indexes = [
            models.Index(fields=['ticket_type'], name='analytics_ticket_idx'),
        ]

    def __str__(self):
        return f"{self.ticket_type.name} - {self.total_sold} sold"
