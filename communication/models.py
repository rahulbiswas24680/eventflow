from django.db import models
from django.conf import settings


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    notification_type = models.CharField(max_length=20)
    is_read = models.BooleanField(default=False)
    link = models.URLField(max_length=200, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='notif_user_idx'),
            models.Index(fields=['user', 'is_read'], name='notif_user_read_idx'),
        ]

    def __str__(self):
        return self.message[:20]
