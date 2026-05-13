from django.contrib import admin
from django.apps import apps
from django.utils.html import format_html


@admin.register(apps.get_model('events', 'TicketType'))
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'event', 'price', 'currency', 'stripe_price_id_status', 'created_at']
    list_filter = ['currency', 'created_at']
    search_fields = ['name', 'event__name']
    readonly_fields = ['stripe_price_id', 'created_at']
    
    def stripe_price_id_status(self, obj):
        if obj.stripe_price_id:
            return format_html('<span style="color: green;">✓ Created</span>')
        return format_html('<span style="color: red;">✗ Missing</span>')
    stripe_price_id_status.short_description = 'Stripe Price'
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        return actions
    
    def recreate_stripe_prices(self, request, queryset):
        from .tasks import create_stripe_product_for_ticket
        
        count = 0
        for ticket_type in queryset:
            create_stripe_product_for_ticket.delay(str(ticket_type.id))
            count += 1
        
        self.message_user(request, f'Recreation tasks queued for {count} ticket type(s).')
    recreate_stripe_prices.short_description = 'Recreate Stripe Price for selected ticket types'


@admin.register(apps.get_model('events', 'Event'))
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'organizer', 'start_date', 'venue', 'has_finished_event', 'created_at']
    list_filter = ['has_finished_event', 'start_date', 'created_at']
    search_fields = ['name', 'venue']
    readonly_fields = ['created_at']


@admin.register(apps.get_model('events', 'RSVP'))
class RSVPAdmin(admin.ModelAdmin):
    list_display = ['event', 'attendee', 'status', 'transaction_id', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['event__name', 'attendee__email', 'transaction_id']
    readonly_fields = ['created_at']