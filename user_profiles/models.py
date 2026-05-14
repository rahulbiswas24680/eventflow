from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.text import slugify
from events.models import RSVP

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    profession = models.CharField(max_length=100, blank=True)
    education = models.CharField(max_length=100, blank=True)
    goal = models.CharField(max_length=100, blank=True)
    languages = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    available_roles = models.ManyToManyField('Role', related_name='users')
    current_role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True, related_name='active_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'CustomUser'
        verbose_name_plural = 'CustomUsers'

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Organizer(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='organizers')
    organizer_name = models.CharField(max_length=200, blank=True, null=True)
    organizer_email = models.CharField(max_length=100, blank=True, null=True)
    organizer_phone = models.CharField(max_length=100, blank=True, null=True)
    organizer_address = models.TextField(blank=True, null=True)
    organizer_slug = models.CharField(max_length=200, blank=True, null=True)
    organizer_image = models.ImageField(upload_to='organizer_images/', blank=True, null=True)
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


class Role(models.Model):
    ROLE_TYPES = (
        ('attendee', 'Attendee'),
        ('organizer', 'Organizer'),
    )
    
    name = models.CharField(max_length=50, choices=ROLE_TYPES, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'roles'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
    
    def __str__(self):
        return self.name