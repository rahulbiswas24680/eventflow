from django.contrib.auth.models import User
from django.db import models

from events.models import RSVP


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    phone = models.CharField(max_length=20, blank=True)
    profession = models.CharField(max_length=100, blank=True)
    education = models.CharField(max_length=100, blank=True)
    goal = models.CharField(max_length=100, blank=True)
    languages = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    # image = models.ImageField(upload_to='profile_images/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'UserProfile'
        verbose_name_plural = 'UserProfiles'

    def __str__(self):
        return self.user.first_name + '- Profile'

    def save(self, *args, **kwargs):
        # Custom save logic here
        super().save(*args, **kwargs)


class UserRSVPHistory(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.PROTECT)
    rsvp = models.ForeignKey(RSVP, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'UserRSVPHistory'
        verbose_name_plural = 'UserRSVPHistories'

    def __str__(self):
        return 'RSVP History - ' + self.user_profile.user.username

    def save(self, *args, **kwargs):
        # Custom save logic here
        super().save(*args, **kwargs)
