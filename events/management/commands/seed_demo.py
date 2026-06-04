from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from events.models import Event, RSVP, TicketType
from payments.models import Transaction
from user_profiles.models import Organizer, Role

User = get_user_model()


class Command(BaseCommand):
    help = "Seed a demo event with sample data for testing"

    def handle(self, *args, **options):
        demo_title = "TechSummit 2026 — Build, Ship, Repeat"
        existing = Event.objects.filter(name=demo_title).first()
        if existing:
            self.stdout.write(self.style.WARNING(f"Demo event already exists: {existing.id}"))
            return

        organizer_user, _ = User.objects.get_or_create(
            email="demo@eventflow.com",
            defaults={"username": "demoorganizer", "is_active": True},
        )
        if not organizer_user.pk:
            organizer_user.set_unusable_password()
            organizer_user.save()

        attendee_user, _ = User.objects.get_or_create(
            email="attendee@demo.com",
            defaults={"username": "demoattendee", "is_active": True},
        )
        if not attendee_user.pk:
            attendee_user.set_unusable_password()
            attendee_user.save()

        role, _ = Role.objects.get_or_create(name="organizer")
        organizer_user.available_roles.add(role)
        organizer_user.current_role = role
        organizer_user.save()

        att_role, _ = Role.objects.get_or_create(name="attendee")
        attendee_user.available_roles.add(att_role)
        attendee_user.current_role = att_role
        attendee_user.save()

        org, _ = Organizer.objects.get_or_create(
            user=organizer_user,
            defaults={
                "organizer_name": "Demo Organizer",
                "organizer_email": "demo@eventflow.com",
                "organizer_phone": "+91XXXXXXXXXX",
                "is_active": True,
                "created_by": organizer_user,
                "modified_by": organizer_user,
            },
        )

        event_date = timezone.make_aware(datetime.now() + timedelta(days=45))
        event = Event.objects.create(
            organizer=org,
            name=demo_title,
            description="""Join us for India's most practical tech conference. No fluff, no vendor pitches — just real engineers building real things.

## What to expect:
- **Live coding sessions** — Watch senior engineers build production apps
- **Workshops** — Get your hands dirty with Go, Rust, and Kubernetes
- **Community** — Meet 500+ developers who actually ship code

### Past attendees say:
> "Best conference I've attended. Left with 3 working projects." — Priya, SDE2 at Razorpay

> "No PowerPoint engineering. Just real code on real problems." — Arjun, CTO of a YC startup

**Early Bird tickets sold out in 48 hours last year.** Grab yours before they're gone.""",
            description_html="<p>Join us for India's most practical tech conference.</p>",
            date=event_date,
            location="NIMHANS Convention Centre, Bangalore",
            is_virtual=False,
            is_published=True,
            is_active=True,
        )

        early_bird = TicketType.objects.create(
            event=event, name="Early Bird", price=499, quantity_available=0,
        )

        general = TicketType.objects.create(
            event=event, name="General Admission", price=799, quantity_available=200,
        )

        TicketType.objects.create(
            event=event, name="VIP — Front Row + Swag Kit", price=1499, quantity_available=50,
        )

        Transaction.objects.create(
            user=attendee_user,
            ticket_type=early_bird,
            currency="INR",
            amount=499,
            quantity=1,
            payment_method="stripe",
            transaction_id="demo_txn_001",
            payment_status="success",
        )

        Transaction.objects.create(
            user=attendee_user,
            ticket_type=general,
            currency="INR",
            amount=799,
            quantity=2,
            payment_method="stripe",
            transaction_id="demo_txn_002",
            payment_status="success",
        )

        RSVP.objects.bulk_create([
            RSVP(
                transaction_id="demo_txn_001", event=event, attendee=attendee_user,
                ticket_qty=1, total_charge=499,
                is_active=False, is_completed=True, is_attended=True,
            ),
            RSVP(
                transaction_id="demo_txn_002", event=event, attendee=attendee_user,
                ticket_qty=2, total_charge=1598,
                is_active=False, is_completed=True, is_attended=False,
            ),
        ])

        self.stdout.write(self.style.SUCCESS(f"Demo event created: {event.id} — '{demo_title}'"))
        self.stdout.write(f"  Login: demo@eventflow.com (no password set — use admin)")
        self.stdout.write(f"  Tickets: Early Bird (SOLD OUT), General (₹799), VIP (₹1499)")
