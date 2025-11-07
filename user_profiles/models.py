from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.text import slugify
from events.models import RSVP

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    groups = models.ManyToManyField(Group, related_name='customuser_groups', blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name='customuser_user_permissions', blank=True)
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
        verbose_name = 'CustomUser'
        verbose_name_plural = 'CustomUsers'

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class UserRSVPHistory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, null=True, blank=True)
    rsvp = models.ForeignKey(RSVP, on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'UserRSVPHistory'
        verbose_name_plural = 'UserRSVPHistories'

    def __str__(self):
        return 'RSVP History - ' + self.user.email

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Organizer(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.PROTECT)
    organizer_name = models.CharField(max_length=200, blank=True, null=True)
    organizer_email = models.CharField(max_length=100, blank=True, null=True)
    organizer_phone = models.CharField(max_length=100, blank=True, null=True)
    organizer_address = models.TextField(blank=True, null=True)
    organizer_slug = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='organizer_created_by')
    modified_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='organizer_modified_by', null=True, blank=True)

    def __str__(self):
        return self.organizer_name

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Organizer'
        verbose_name_plural = 'Organizers'
    
    def save(self, *args, **kwargs):
        self.organizer_slug = slugify(self.organizer_name)
        super().save(*args, **kwargs)
