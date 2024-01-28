
from django.db import models
from events.models import Event, TicketType


class EventAnalytics(models.Model):
    event = models.OneToOneField(Event, on_delete=models.PROTECT)
    total_tickets = models.IntegerField(default=0)
    tickets_sold = models.IntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    unique_visits = models.IntegerField(default=0)
    total_visits = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'EventAnalytics'

    def __str__(self):
        return self.event.name

    def save(self, *args, **kwargs):
        # Custom save logic here
        super().save(*args, **kwargs)


class TicketTypeAnalytics(models.Model):
    ticket_type = models.OneToOneField(TicketType, on_delete=models.PROTECT)
    tickets_sold = models.IntegerField(default=0)
    tickets_remaining = models.IntegerField(default=0)
    gross_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'TicketTypeAnalytics'

    def __str__(self):
        return self.ticket_type + '-' + self.tickets_sold + ' sold'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
