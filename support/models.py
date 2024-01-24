from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

PRIORITY_CHOICES = (
    ('L', 'Low'),
    ('M', 'Medium'),
    ('H', 'High'),
)

STATUS_CHOICES = (
    ('Open', 'Open'),
    ('In Progress', 'In Progress'),
    ('Closed', 'Closed')
)


class SupportTicket(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    priority = models.CharField(
        max_length=1, choices=PRIORITY_CHOICES, default='M')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='Open')
    assigned_to = models.ForeignKey(
        User, related_name='assigned_tickets', 
        on_delete=models.PROTECT, null=True, blank=True)

    resolution = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def resolve(self):
        self.status = 'Closed'
        self.resolved_at = timezone.now()
        self.save()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SupportTicket'
        verbose_name_plural = 'SupportTickets'

    def __str__(self):
        return self.subject[:20] + ' -' + self.user.email 

    def save(self, *args, **kwargs):
        # Custom save logic here
        super().save(*args, **kwargs)
