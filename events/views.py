import json
import markdown
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, F, Q, Sum, OuterRef, Subquery
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from weasyprint import HTML

from qr_codes.models import QRCode
from user_profiles.models import CustomUser, Organizer, Role

from .api.serializers import EventDetailSerializer, EventSerializer
from .models import RSVP, Event, EventImage, TicketType


@login_required
def user_profile(request):
    """
    Display user profile with recent activity
    """
    user = request.user
    context = {'user': user}
    
    # Check current role
    is_organizer = hasattr(user, 'current_role') and user.current_role.name == 'organizer'
    context['is_organizer'] = is_organizer
    
    if is_organizer:
        # Get recent organized events
        recent_events = Event.objects.filter(organizer__user=user).order_by('-created_at')[:5]
        
        # Calculate stats for these events
        for event in recent_events:
            # Get attendance stats
            stats = RSVP.objects.filter(event=event, is_completed=True).aggregate(
                registered=Count('id'),
                revenue=Sum('total_charge')
            )
            event.registered_count = stats['registered'] or 0
            event.revenue = stats['revenue'] or 0
            
        context['recent_events'] = recent_events
    else:
        # Get recent RSVPs (events attended/registered)
        recent_rsvps = RSVP.objects.filter(attendee=user).select_related('event').order_by('-created_at')[:5]
        context['recent_rsvps'] = recent_rsvps
    
    return render(request, "events/profile.html", context)


class OrganizerForm(forms.ModelForm):
    # Remove privacy and terms fields since they're not in the model
    # These are not needed for the organizer model itself
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make organizer_name required
        self.fields['organizer_name'].required = True
        # Add custom validation for empty fields
        for field_name in self.fields:
            self.fields[field_name].widget.attrs['required'] = 'required'
    
    class Meta:
        model = Organizer
        fields = [
            "organizer_name",
            "organizer_email",
            "organizer_phone",
            "organizer_address",
            "organizer_slug",
            "is_active",
        ]
        widgets = {
            'organizer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter organizer name'
            }),
            'organizer_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter organizer email'
            }),
            'organizer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter organizer phone'
            }),
            'organizer_address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter organizer address',
                'rows': 3
            }),
            'organizer_slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., my-company-name',
                'title': 'This will be the URL your events can be found at. We will also use this as an abbreviation of your account in some other places.'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean_organizer_slug(self):
        """Clean and validate the organizer slug"""
        slug = self.cleaned_data.get('organizer_slug')
        if slug:
            # Clean the slug
            slug = slugify(slug)
            
            # Check if slug already exists (excluding current instance in edit mode)
            queryset = Organizer.objects.filter(organizer_slug=slug)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(
                    "This slug is already in use. Please choose a different one."
                )
        return slug
    
    def clean_organizer_email(self):
        """Clean and validate email"""
        email = self.cleaned_data.get('organizer_email')
        if email:
            # Check if email already exists (excluding current instance in edit mode)
            queryset = Organizer.objects.filter(organizer_email=email)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(
                    "This email is already associated with another organizer."
                )
        return email

    def clean_organizer_name(self):
        """Clean and validate organizer name"""
        name = self.cleaned_data.get('organizer_name')
        if not name or not name.strip():
            raise forms.ValidationError("Organizer name is required.")
        return name.strip()
    
    def save(self, commit=True, user=None):
        """Override save to handle created_by and modified_by"""
        instance = super().save(commit=False)
        
        if not instance.pk:  # New instance
            if user:
                instance.created_by = user
                instance.modified_by = user
        else:  # Existing instance
            if user:
                instance.modified_by = user
        
        if commit:
            instance.save()
        
        return instance


class OrganizerUpdateView(LoginRequiredMixin, UpdateView):
    model = Organizer
    form_class = OrganizerForm
    template_name = "events/organizer_create.html"
    success_url = reverse_lazy("organizers-list")
    login_url = '/auth/login/'

    def form_valid(self, form):
        try:
            form.save()
            messages.success(self.request, "Organizer profile updated successfully!")
            return redirect('organizers-list')
        except Exception as e:
            messages.error(self.request, f"Error updating organizer profile: {str(e)}")
            return redirect('organizer-edit', self.object.id)
        

class OrganizerDeleteView(LoginRequiredMixin, DeleteView):
    model = Organizer
    template_name = "events/organizer_delete.html"
    success_url = reverse_lazy("organizers-masters")
    login_url = '/auth/login/'


class OrganizerListView(LoginRequiredMixin, ListView):
    model = Organizer
    template_name = "events/organizers_list.html"
    context_object_name = "organizers"
    login_url = '/auth/login/'

    def get_queryset(self):
        qs = Organizer.objects.filter(user=self.request.user)
        print(qs, self.request.user)
        return qs



# @login_required
def events_home(request):
    # Publicly visible events
    events = Event.objects.filter(is_published=True, is_active=True).select_related('organizer')

    context = {"events": events}

    if request.user.is_authenticated:
        # Get organizer profile if user is an organizer
        organizer = Organizer.objects.filter(user=request.user).first()
        if organizer:
            context["can_create_event"] = True
            # Show user's own events (drafts/unpublished)
            user_events = Event.objects.filter(organizer=organizer).select_related('organizer')
            context["user_events"] = user_events
    else:
        # Guest users can only see published events
        context["can_create_event"] = False

    return render(request, "events/events_home.html", context)


@login_required
def event_detail(request, event_id):
    event = Event.objects.select_related('organizer').prefetch_related('images', 'tickettype_set').get(id=event_id)
    images = event.images.all()
    tickets = event.tickettype_set.all()
    context = {"event": event, "tickets": tickets, "images": images}
    return render(request, "events/event_detail.html", context)


@login_required(login_url='/auth/login/')
def create_event(request):
    """Create a new event with tickets and images"""
    
    if request.method == "POST":
        try:
            # Get basic event data
            organizer_id = request.POST.get('organizer')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            date_str = request.POST.get('date', '').strip()
            location = request.POST.get('location', '').strip()
            is_virtual = request.POST.get('is_virtual') == 'on'
            is_published = request.POST.get('is_published') == 'on'
            
            # Validate required fields
            if not organizer_id:
                messages.error(request, "Please select an organizer")
                return redirect('create-event')
                
            if not name:
                messages.error(request, "Event name is required")
                return redirect('create-event')
                
            if not date_str:
                messages.error(request, "Event date is required")
                return redirect('create-event')
            
            # Get organizer and verify ownership
            try:
                organizer = Organizer.objects.get(id=organizer_id, user=request.user, is_active=True)
            except Organizer.DoesNotExist:
                messages.error(request, "Invalid organizer selected")
                return redirect('create-event')
            
            # Parse datetime
            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
                event_date = timezone.make_aware(event_date) if timezone.is_naive(event_date) else event_date
            except ValueError as e:
                messages.error(request, f"Invalid date format: {str(e)}")
                return redirect('create-event')
            
            # Create event
            # Process markdown description
            description_html = mark_safe(markdown.markdown(description, extensions=['extra']))
            
            event = Event.objects.create(
                organizer=organizer,
                name=name,
                description=description,
                description_html=description_html,
                date=event_date,
                location=location,
                is_virtual=is_virtual,
                is_published=is_published,
                is_active=True
            )
            
            print(f"✅ Event created: {event.name} (ID: {event.id})")
            
            # Handle event images
            images = request.FILES.getlist('images')
            print(f"📸 Processing {len(images)} event images")
            for image in images:
                if image and image.size > 0:  # Check if file is valid
                    EventImage.objects.create(event=event, image=image)
                    print(f"  ✓ Saved image: {image.name}")
            
            # Handle tickets - find all ticket indices
            ticket_indices = set()
            for key in request.POST.keys():
                if key.startswith('ticket_name_'):
                    index = key.split('_')[-1]
                    ticket_indices.add(index)
            
            print(f"🎟️  Found {len(ticket_indices)} ticket(s) to process")
            
            # Create tickets
            tickets_created = 0
            for index in sorted(ticket_indices, key=lambda x: int(x) if x.isdigit() else 0):
                ticket_name = request.POST.get(f'ticket_name_{index}', '').strip()
                ticket_price_str = request.POST.get(f'ticket_price_{index}', '').strip()
                ticket_quantity_str = request.POST.get(f'ticket_quantity_{index}', '').strip()
                discount_code = request.POST.get(f'ticket_discount_code_{index}', '').strip()
                ticket_image = request.FILES.get(f'ticket_image_{index}')
                
                # Skip if ticket name is empty
                if not ticket_name:
                    print(f"  ⚠️  Skipping ticket {index} - no name")
                    continue
                
                # Validate price
                if not ticket_price_str:
                    messages.error(request, f"Ticket '{ticket_name}' is missing price")
                    event.delete()  # Rollback
                    return redirect('create-event')
                
                try:
                    ticket_price = Decimal(ticket_price_str)
                    if ticket_price < 0:
                        raise ValueError("Price cannot be negative")
                    # Check if price is reasonable (less than 1 million)
                    if ticket_price > 999999:
                        raise ValueError("Price is too large")
                except (ValueError, InvalidOperation) as e:
                    messages.error(request, f"Invalid price for ticket '{ticket_name}': {ticket_price_str}")
                    event.delete()  # Rollback
                    return redirect('create-event')
                
                # Validate quantity
                if not ticket_quantity_str:
                    messages.error(request, f"Ticket '{ticket_name}' is missing quantity")
                    event.delete()  # Rollback
                    return redirect('create-event')
                
                try:
                    ticket_quantity = int(ticket_quantity_str)
                    if ticket_quantity < 1:
                        raise ValueError("Quantity must be at least 1")
                    # Check if quantity is reasonable (less than 1 million)
                    if ticket_quantity > 999999:
                        raise ValueError("Quantity is too large")
                except (ValueError, TypeError) as e:
                    messages.error(request, f"Invalid quantity for ticket '{ticket_name}': {ticket_quantity_str}")
                    event.delete()  # Rollback
                    return redirect('create-event')
                
                # Create ticket
                try:
                    ticket = TicketType.objects.create(
                        event=event,
                        name=ticket_name,
                        price=ticket_price,
                        quantity_available=ticket_quantity,
                        discount_code=discount_code if discount_code else None,
                        image=ticket_image if ticket_image and ticket_image.size > 0 else None
                    )
                    print(f"  ✓ Created ticket: {ticket.name} - ₹{ticket.price} ({ticket.quantity_available} available)")
                    tickets_created += 1
                except Exception as e:
                    print(f"  ✗ Error creating ticket {ticket_name}: {str(e)}")
                    messages.error(request, f"Error creating ticket '{ticket_name}': {str(e)}")
                    event.delete()  # Rollback
                    return redirect('create-event')
            
            # Check if at least one ticket was created
            if tickets_created == 0:
                messages.error(request, "At least one valid ticket is required")
                event.delete()  # Rollback
                return redirect('create-event')
            
            messages.success(request, f"🎉 Event '{name}' created successfully with {tickets_created} ticket(s)!")
            return redirect('event-detail', event.id)
            
        except Exception as e:
            print(f"❌ Unexpected error creating event: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f"Error creating event: {str(e)}")
            return redirect('create-event')
    
    # GET request - show form
    context = {
        'title': 'Create Event',
        'organizers': Organizer.objects.filter(user=request.user, is_active=True),
        'event': None,
        'images': [],
        'tickets': []
    }
    return render(request, 'events/event_form.html', context)

# class EventForm(forms.ModelForm):
#     class Meta:
#         model = Event
#         fields = [
#             "organizer",
#             "name",
#             "description",
#             "date",
#             "location",
#             "is_virtual",
#             "is_published",
#             "is_active",
#         ]
#         widgets = {
#             'organizer': forms.Select(attrs={'class': 'form-control'}),
#             'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Name'}),
#             'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Event Description'}),
#             'date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
#             'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Location'}),
#             'is_virtual': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#         }

@login_required(login_url='/auth/login/')
def update_event(request, pk):
    """Update an existing event"""
    
    # Get event and verify ownership
    event = get_object_or_404(Event, pk=pk, organizer__user=request.user)
    print('???', request.POST, request.FILES)
    
    # Handle both PUT requests and POST requests with _method=PUT
    if request.method == "POST":
        try:
            # Get basic event data
            request_data = request.PUT if request.method == "PUT" else request.POST
            organizer_id = request_data.get('organizer')
            name = request_data.get('name')
            description = request_data.get('description', '')
            date_str = request_data.get('date')
            location = request_data.get('location', '')
            is_virtual = request_data.get('is_virtual') == 'on'
            is_published = request_data.get('is_published') == 'on'
            
            # Validate required fields
            if not organizer_id or not name or not date_str:
                messages.error(request, "Please fill in all required fields (Organizer, Event Name, Date)")
                return redirect('update-event', pk=pk)
            
            # Verify organizer ownership
            organizer = get_object_or_404(Organizer, id=organizer_id, user=request.user, is_active=True)
            
            # Parse datetime
            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
                event_date = timezone.make_aware(event_date) if timezone.is_naive(event_date) else event_date
            except ValueError:
                messages.error(request, "Invalid date format")
                return redirect('update-event', pk=pk)
            
            # Update event
            event.organizer = organizer
            event.name = name
            
            # Process markdown description
            event.description = description
            event.description_html = mark_safe(markdown.markdown(description, extensions=['extra']))
            
            event.date = event_date
            event.location = location
            event.is_virtual = is_virtual
            event.is_published = is_published
            event.save()
            
            # Handle new event images
            new_images = request.FILES.getlist('images')
            for image in new_images:
                EventImage.objects.create(event=event, image=image)
            
# Handle tickets - find all ticket indices
            ticket_indices = set()
            for key in request_data.keys():
                if key.startswith('ticket_name_'):
                    index = key.split('_')[-1]
                    ticket_indices.add(index)
            
            # Get existing tickets and map by ID for better update logic
            existing_tickets = {ticket.id: ticket for ticket in TicketType.objects.filter(event=event)}
            existing_ticket_ids = list(existing_tickets.keys())
            
            # Update or create tickets
            tickets_processed = 0
            updated_ticket_ids = set()
            
            for index in sorted(ticket_indices, key=lambda x: int(x) if x.isdigit() else 0):
                ticket_name = request_data.get(f'ticket_name_{index}')
                ticket_price = request_data.get(f'ticket_price_{index}')
                ticket_quantity = request_data.get(f'ticket_quantity_{index}')
                discount_code = request_data.get(f'ticket_discount_code_{index}', '')
                ticket_image = request.FILES.get(f'ticket_image_{index}')
                
                # Validate ticket data
                if ticket_name and ticket_price and ticket_quantity:
                    try:
                        # Parse values
                        price_val = float(ticket_price)
                        quantity_val = int(ticket_quantity)
                        
                        # Try to find an existing ticket to update
                        ticket_updated = False
                        for ticket_id, ticket in existing_tickets.items():
                            if ticket.name == ticket_name:  # Match by name (could be improved with ticket_id from form)
                                # Update existing ticket
                                ticket.name = ticket_name
                                ticket.price = price_val
                                ticket.quantity_available = quantity_val
                                ticket.discount_code = discount_code if discount_code else None
                                if ticket_image:
                                    ticket.image = ticket_image
                                ticket.save()
                                updated_ticket_ids.add(ticket_id)
                                tickets_processed += 1
                                ticket_updated = True
                                break
                        
                        if not ticket_updated:
                            # Create new ticket
                            new_ticket = TicketType.objects.create(
                                event=event,
                                name=ticket_name,
                                price=price_val,
                                quantity_available=quantity_val,
                                discount_code=discount_code if discount_code else None,
                                image=ticket_image if ticket_image else None
                            )
                            updated_ticket_ids.add(new_ticket.id)
                            tickets_processed += 1
                    
                    except (ValueError, Exception) as e:
                        print(f"Error processing ticket {index}: {e}")
            
            # Delete tickets that were not updated (removed from form)
            for ticket_id in existing_ticket_ids:
                if ticket_id not in updated_ticket_ids:
                    existing_tickets[ticket_id].delete()
            
            messages.success(request, f"Event '{name}' updated successfully!")
            return redirect('our-events')
            
        except Exception as e:
            print(f"Error updating event: {e}")
            messages.error(request, f"Error updating event: {str(e)}")
            return redirect('update-event', pk=pk)
    
    # GET request - show form with existing data
    context = {
        'title': 'Edit Event',
        'event': event,
        'images': event.images.all(),
        'organizers': Organizer.objects.filter(user=request.user, is_active=True),
        'tickets': TicketType.objects.filter(event=event)
    }
    return render(request, 'events/event_form.html', context)

class OrganizerCreateView(LoginRequiredMixin, CreateView):
    model = Organizer
    form_class = OrganizerForm
    template_name = "events/organizer_create.html"
    success_url = reverse_lazy("organizers-list")
    login_url = '/auth/login/'

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.created_by = self.request.user
        form.instance.modified_by = self.request.user
        messages.success(self.request, "Organizer profile created successfully!")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        print("❌ Form is invalid:", form.errors, form.non_field_errors())
        return super().form_invalid(form)


def ticket_preview(request, rsvp_id):
    # Get the RSVP/ticket object
    rsvp = get_object_or_404(RSVP, id=rsvp_id)
    qr_code = QRCode.objects.get(transaction_id=rsvp.transaction)
    print('--', qr_code)
    
    # Verify user has permission to view this ticket
    if not request.user.is_authenticated or (rsvp.attendee != request.user and not request.user.is_staff):
        return HttpResponse("Unauthorized", status=403)
    
    context = {
        'rsvp': rsvp,
        'transaction': rsvp.transaction,
        'event': rsvp.event,
        'ticket_type': rsvp.transaction.ticket_type if rsvp.transaction else None,
        'qr_code': qr_code
    }
    
    # If PDF download requested
    if request.GET.get('download') == 'pdf':
        return generate_ticket_pdf(context, request)
    
    return render(request, 'events/ticket_preview.html', context)

def generate_ticket_pdf(context, request):
    """Generate PDF version of the ticket"""
    html_string = render_to_string('events/ticket_pdf.html', context)
    
    # Create PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()
    
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket-{context["rsvp"].id}.pdf"'
    return response

@login_required
def switch_role(request):
    """
    Switch the current user's active role and redirect to dashboard.
    """
    if request.method == 'POST':
        selected_role_id = request.POST.get('role_id')

        if not selected_role_id:
            messages.error(request, 'No role selected.')
            return redirect('dashboard')

        # Get role object safely
        role = get_object_or_404(Role, id=selected_role_id)

        user = request.user

        # Ensure user has access to this role
        if role not in user.available_roles.all():
            return HttpResponseForbidden("You don't have permission to use this role.")

        # Switch current role
        user.current_role = role
        user.save()

        # Update session
        request.session['current_role_id'] = role.id
        request.session['current_role_name'] = role.name

        messages.success(request, f'Switched to {role.name} role successfully.')

    # Always redirect to dashboard, no matter what
    return redirect('dashboard')



@login_required
def dashboard(request):
    """
    Professional dashboard with charts and analytics
    """
    # Ensure user_profile is CustomUser instance
    user_profile = request.user
    today = timezone.now()
    months_ago_12 = (today - timedelta(days=365)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Organizer Dashboard
    if hasattr(user_profile, 'current_role') and user_profile.current_role.name == 'organizer':
        # Get organizer's events
        organized_events = Event.objects.filter(organizer__user=request.user)
        
        # Key Metrics
        total_events = organized_events.count()
        active_events = organized_events.filter(
            date__date=today.date(), # Compare only the date part
            is_active=True,
            is_published=True
        ).count()
        upcoming_events = organized_events.filter(date__gt=today, is_active=True, is_published=True).count()
        past_events = organized_events.filter(date__lt=today, is_active=True, is_published=True).count()
        
        # Attendance Analytics
        total_attendees = RSVP.objects.filter(
            event__organizer__user=request.user,
            is_completed=True # Only count completed RSVPs as attendees
        ).count()
        
        # Revenue
        total_revenue = RSVP.objects.filter(
            event__organizer__user=request.user,
            is_completed=True
        ).aggregate(total=Sum('total_charge'))['total'] or 0

        
        # Get ticket type capacity per event
        ticket_capacity_subquery = TicketType.objects.filter(
            event_id=OuterRef('id')
        ).values('event_id').annotate(
            total_capacity=Sum('quantity_available')
        ).values('total_capacity')[:1]
        
        # Get RSVP counts per event
        rsvp_count_subquery = RSVP.objects.filter(
            event_id=OuterRef('id'),
            is_completed=True
        ).values('event_id').annotate(
            count=Count('id')
        ).values('count')[:1]
        
        # Get attended count (is_attended field)
        attended_count_subquery = RSVP.objects.filter(
            event_id=OuterRef('id'),
            is_attended=True
        ).values('event_id').annotate(
            count=Count('id')
        ).values('count')[:1]
        
        # Optimized query - single database hit with annotations
        recent_events = organized_events.order_by('-created_at')[:5].annotate(
            capacity=Subquery(ticket_capacity_subquery),
            registered=Subquery(rsvp_count_subquery),
            attended=Subquery(attended_count_subquery)
        )
        
        registration_data = []
        for event in recent_events:
            registered = event.registered or 0
            attended = event.attended or 0
            conversion_rate = (attended / registered * 100) if registered > 0 else 0
            
            registration_data.append({
                'event': event.name,
                'capacity': event.capacity or 0,
                'registered': registered,
                'attended': attended,
                'conversion_rate': round(conversion_rate, 1)
            })
        
        # Monthly Growth Chart Data - Optimized with single query using TruncMonth
        from django.db.models.functions import TruncMonth
        
        rsvp_by_month = RSVP.objects.filter(
            event__organizer__user=request.user,
            is_completed=True,
            created_at__gte=months_ago_12
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            attendees=Count('id'),
            revenue=Sum('total_charge')
        ).order_by('month')
        
        events_by_month = organized_events.filter(
            created_at__gte=months_ago_12
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        # Create lookup dicts for O(1) access
        rsvp_lookup = {item['month'].strftime('%Y-%m'): item for item in rsvp_by_month}
        event_lookup = {item['month'].strftime('%Y-%m'): item for item in events_by_month}
        
        monthly_data = []
        for i in range(12):
            month_date = (today - timedelta(days=30*i)).replace(day=1)
            month_key = month_date.strftime('%Y-%m')
            
            month_rsvp = rsvp_lookup.get(month_key, {})
            month_event = event_lookup.get(month_key, {})
            
            monthly_data.append({
                'month': month_date.strftime('%b %Y'),
                'events': month_event.get('count', 0),
                'attendees': month_rsvp.get('attendees', 0),
                'revenue': float(month_rsvp.get('revenue', 0) or 0)
            })
        
        monthly_data.reverse()
        
        # Event Type Distribution (assuming 'category' field exists in Event model metadata)
        event_categories = organized_events.values('metadata__category').annotate(
            count=Count('id')
        ).order_by('-count') if Event._meta.get_field('metadata').null else [] # Check if metadata field exists and is not null
        
        context = {
            'role': 'organizer',
            'total_events': total_events,
            'active_events': active_events,
            'upcoming_events': upcoming_events,
            'past_events': past_events,
            'total_attendees': total_attendees,
            'total_revenue': total_revenue,
            'registration_data': registration_data,
            'monthly_data_json': json.dumps(monthly_data, cls=DjangoJSONEncoder),
            'event_categories': event_categories,
            'recent_events': organized_events.order_by('-created_at')[:5],
        }
    
    # Attendee Dashboard
    else:
        # Get attendee's RSVPs
        attendee_rsvps = RSVP.objects.filter(attendee=request.user)
        
        # Key Metrics
        total_registered = attendee_rsvps.count()
        attended_events = attendee_rsvps.filter(is_completed=True).count()
        upcoming_events = attendee_rsvps.filter(
            event__date__gt=today,
            is_completed=True # Only count completed RSVPs for upcoming
        ).count()
        cancelled_events = attendee_rsvps.filter(is_cancelled=True).count()
        
        # Event Categories attended (assuming 'category' field exists in Event model metadata)
        if Event._meta.get_field('metadata').null:
            category_distribution = attendee_rsvps.filter(
                is_completed=True
            ).values('event__metadata__category').annotate(count=Count('id')).order_by('-count')
        else:
            category_distribution = []
        
        # Monthly Activity
        monthly_activity = []
        for i in range(6):
            month_start = (today - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            
            month_registrations = attendee_rsvps.filter(
                created_at__range=[month_start, month_end]
            ).count()
            month_attended = attendee_rsvps.filter(
                event__date__range=[month_start, month_end],
                is_completed=True
            ).count()
            
            monthly_activity.append({
                'month': month_start.strftime('%b %Y'),
                'registrations': month_registrations,
                'attended': month_attended
            })
        
        monthly_activity.reverse()
        
        context = {
            'role': 'attendee',
            'total_registered': total_registered,
            'attended_events': attended_events,
            'upcoming_events': upcoming_events,
            'cancelled_events': cancelled_events,
            'category_distribution': category_distribution,
            'monthly_activity_json': json.dumps(monthly_activity, cls=DjangoJSONEncoder),
            'recent_registrations': attendee_rsvps.select_related('event').order_by('-created_at')[:5],
        }
    
    return render(request, 'events/dashboard.html', context)

@login_required
def our_events(request):
    """
    Organizer-only view to manage their events with pagination
    """
    # Only organizers can access this page
    if not hasattr(request.user, 'current_role') or request.user.current_role.name != 'organizer':
        return HttpResponseForbidden("Only organizers can access this page.")
    
    events = Event.objects.filter(organizer__user=request.user).order_by('-created_at')
    
    # Filter events by status
    status_filter = request.GET.get('status', 'all')
    today = timezone.now()
    if status_filter == 'active':
        events = events.filter(
            date__date=today.date(), # Compare only the date part
            is_active=True,
            is_published=True
        )
    elif status_filter == 'upcoming':
        events = events.filter(date__gt=today, is_active=True, is_published=True)
    elif status_filter == 'past':
        events = events.filter(date__lt=today, is_active=True, is_published=True)
    elif status_filter == 'draft':
        events = events.filter(is_published=False)  # Draft events not published
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        events = events.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    # Get total count before pagination
    total_events = events.count()
    
    # Pagination
    paginator = Paginator(events, 10)  # Show 10 events per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get event IDs for the current page to optimize database queries
    event_ids = [event.id for event in page_obj]
    
    # Get attendance stats for all events on current page in a single query
    attendance_stats = {}
    if event_ids:
        stats = RSVP.objects.filter(
            event_id__in=event_ids,
            is_cancelled=False
        ).values('event_id').annotate(
            registered_count=Count('id'),
            attended_count=Count('id', filter=Q(is_attended=True))
        )
        
        for stat in stats:
            attendance_stats[stat['event_id']] = {
                'registered_count': stat['registered_count'],
                'attended_count': stat['attended_count'],
                'attendance_rate': (stat['attended_count'] / stat['registered_count'] * 100) if stat['registered_count'] > 0 else 0
            }
    
    # Get ticket capacity for all events on current page in a single query
    ticket_capacity_map = {}
    if event_ids:
        ticket_totals = TicketType.objects.filter(
            event_id__in=event_ids
        ).values('event_id').annotate(
            total_capacity=Sum('quantity_available')
        )
        for tc in ticket_totals:
            ticket_capacity_map[tc['event_id']] = tc['total_capacity']
    
    # Add attendance stats and other properties to each event
    for event in page_obj:
        stats = attendance_stats.get(event.id, {
            'registered_count': 0,
            'attended_count': 0,
            'attendance_rate': 0
        })
        
        event.registered_count = stats['registered_count']
        event.attended_count = stats['attended_count']
        event.attendance_rate = stats['attendance_rate']
        event.is_draft = not event.is_published  # Add draft status
        
        # Get max attendees from pre-fetched ticket capacity
        event.max_attendees = ticket_capacity_map.get(event.id, 0)
    
    context = {
        'events': page_obj,  # Use page_obj instead of events
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_events': total_events,
        'is_paginated': page_obj.has_other_pages(),
        'now': timezone.now(),  # Add current time for template comparisons
    }
    
    return render(request, 'events/our_events.html', context)


@login_required
def manage_attendees(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Ensure the logged-in user is the organizer of this event
    if not hasattr(request.user, 'current_role') or request.user.current_role.name != 'organizer' or event.organizer.user != request.user:
        messages.error(request, "You are not authorized to manage attendees for this event.")
        return redirect('dashboard')

    rsvps = RSVP.objects.filter(event=event).select_related('transaction__ticket_type').order_by('-created_at')
    ticket_types = (rsvps.filter(transaction__ticket_type__isnull=False)
                        .values(
                            ticket_id=F('transaction__ticket_type__id'), 
                            ticket_name=F('transaction__ticket_type__name')
                        ).distinct())
    print(ticket_types)
    context = {
        'event': event,
        'ticket_types': ticket_types
    }
    return render(request, 'events/manage_attendees.html', context)


# AJAX view for dashboard charts
@login_required
def dashboard_chart_data(request):
    """
    Provide JSON data for dashboard charts
    """
    user_profile = request.user
    chart_type = request.GET.get('chart_type', 'monthly_growth')
    
    if hasattr(user_profile, 'current_role') and user_profile.current_role.name == 'organizer':
        organized_events = Event.objects.filter(organizer__user=request.user)
        
        if chart_type == 'monthly_growth':
            # Generate monthly growth data
            today = timezone.now()
            data = []
            
            for i in range(12):
                month_start = (today - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_end = (month_start + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
                
                month_events = organized_events.filter(
                    created_at__range=[month_start, month_end]
                )
                month_attendees = RSVP.objects.filter(
                    event__organizer__user=request.user,
                    created_at__range=[month_start, month_end],
                    is_completed=True
                ).count()
                
                month_revenue = RSVP.objects.filter(
                    event__organizer__user=request.user,
                    created_at__range=[month_start, month_end],
                    is_completed=True
                ).aggregate(total=Sum('total_charge'))['total'] or 0
                
                data.append({
                    'month': month_start.strftime('%b %Y'),
                    'events': month_events.count(),
                    'attendees': month_attendees,
                    'revenue': month_revenue
                })
            
            data.reverse()
            return JsonResponse({'data': data})
        
        elif chart_type == 'event_category_distribution':
            event_categories = organized_events.values('metadata__category').annotate(
                count=Count('id')
            ).order_by('-count') if Event._meta.get_field('metadata').null else []
            return JsonResponse({'data': list(event_categories)})
    
    else:
        # Treat as attendee (default)
        attendee_rsvps = RSVP.objects.filter(attendee=request.user)
        
        if chart_type == 'monthly_activity':
            monthly_activity = []
            today = timezone.now()
            for i in range(6):
                month_start = (today - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_end = (month_start + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
                
                month_registrations = attendee_rsvps.filter(
                    created_at__range=[month_start, month_end]
                ).count()
                month_attended = attendee_rsvps.filter(
                    event__date__range=[month_start, month_end],
                    is_completed=True
                ).count()
                
                monthly_activity.append({
                    'month': month_start.strftime('%b %Y'),
                    'registrations': month_registrations,
                    'attended': month_attended
                })
            monthly_activity.reverse()
            return JsonResponse({'data': monthly_activity})
        
        elif chart_type == 'category_distribution':
            if Event._meta.get_field('metadata').null:
                category_distribution = attendee_rsvps.filter(
                    is_completed=True
                ).values('event__metadata__category').annotate(count=Count('id')).order_by('-count')
            else:
                category_distribution = []
            return JsonResponse({'data': list(category_distribution)})
            
    return JsonResponse({'data': []})
