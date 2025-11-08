from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from user_profiles.models import Organizer
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile


from .api.serializers import EventDetailSerializer, EventSerializer
from .models import Event, TicketType, EventImage, RSVP
from qr_codes.models import QRCode


class OrganizerForm(forms.ModelForm):
    # privacy = forms.BooleanField(
    #     label='I have read and agree with the privacy policy',
    #     required=True,
    #     widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    # )
    # terms = forms.BooleanField(
    #     label='I have read and agree with the terms of service',
    #     required=True,
    #     widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    # )

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
                'placeholder': 'Address short form',
                'title': 'This will be the URL your events can be found at. We will also use this as an abbreviation of your account in some other places.'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('privacy') or not cleaned_data.get('terms'):
            raise forms.ValidationError(
                "You must agree to both the privacy policy and terms of service"
            )
        return cleaned_data


class OrganizerUpdateView(LoginRequiredMixin, UpdateView):
    model = Organizer
    form_class = OrganizerForm
    template_name = "events/organizer_create.html"
    success_url = reverse_lazy("organizers-list")
    login_url = '/auth/login/'


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
    event = Event.objects.get(id=event_id)
    images = EventImage.objects.filter(event=event)
    tickets = TicketType.objects.filter(event__id=event_id)
    context = {"event": event, "tickets": tickets, "images": images}
    return render(request, "events/event_detail.html", context)


@login_required
def create_event(request):
    if request.method == "POST":
        organizer_id = request.POST.get("organizer")
        name = request.POST.get("name")
        description = request.POST.get("description")
        date = request.POST.get("date")
        location = request.POST.get("location")
        is_virtual = request.POST.get("is_virtual") == "on"
        is_published = request.POST.get("is_published") == "on"
        
        # Get the organizer object
        try:
            organizer = Organizer.objects.get(id=organizer_id)
        except Organizer.DoesNotExist:
            return HttpResponseBadRequest("Invalid organizer selected")

        if not name or not date:
            return HttpResponseBadRequest("Name and Date are required")
            
        # Create the event first
        event = Event.objects.create(
            organizer=organizer,
            name=name,
            description=description,
            date=date,
            location=location,
            is_virtual=is_virtual,
            is_published=is_published,
            is_active=True,
        )
        
        # Handle event image uploads
        event_images = request.FILES.getlist('images')
        print(f"Received {len(event_images)} event images")
        for image in event_images:
            print(f"Saving event image: {image.name}")
            EventImage.objects.create(event=event, image=image)
            print(f"Event image {image.name} saved successfully")
            
        # Process tickets
        ticket_index = 1
        tickets_created = 0
        
        while True:
            ticket_name = request.POST.get(f"ticket_name_{ticket_index}")
            ticket_price = request.POST.get(f"ticket_price_{ticket_index}")
            ticket_quantity = request.POST.get(f"ticket_quantity_{ticket_index}")
            ticket_discount_code = request.POST.get(f"ticket_discount_code_{ticket_index}")
            ticket_image = request.FILES.get(f"ticket_image_{ticket_index}")
            
            # If we don't have a ticket name at this index, we've processed all tickets
            if not ticket_name:
                break
                
            # Validate required ticket fields
            if not ticket_price or not ticket_quantity:
                return HttpResponseBadRequest(f"Ticket #{ticket_index} is missing required fields. Please provide price and quantity.")
                
            # Create the ticket
            ticket = TicketType.objects.create(
                event=event,
                name=ticket_name,
                price=ticket_price,
                quantity_available=ticket_quantity,
                discount_code=ticket_discount_code if ticket_discount_code else None,
                image=ticket_image if ticket_image else None
            )
            
            print(f"Ticket {ticket.name} created successfully")
            tickets_created += 1
            ticket_index += 1
            
        # Ensure at least one ticket was created
        if tickets_created == 0:
            return HttpResponseBadRequest("At least one ticket is required for the event.")

        # Redirect to event detail page
        return redirect("event-detail", event.id)

    organizers_qs = Organizer.objects.filter(user=request.user)
    context = {'organizers': organizers_qs}
    return render(request, "events/event_form.html", context=context)

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