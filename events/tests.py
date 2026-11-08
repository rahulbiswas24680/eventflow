import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from events.models import Event, TicketType, RSVP
from user_profiles.models import Organizer, Role

User = get_user_model()


@pytest.fixture
def attendee_user(db):
    role, _ = Role.objects.get_or_create(name='attendee')
    user = User.objects.create_user(
        username='attendee_user',
        email='attendee@example.com',
        password='testpassword',
        current_role=role
    )
    user.available_roles.add(role)
    return user


@pytest.fixture
def organizer_user(db):
    role, _ = Role.objects.get_or_create(name='organizer')
    user = User.objects.create_user(
        username='organizer_user',
        email='organizer@example.com',
        password='testpassword',
        current_role=role
    )
    user.available_roles.add(role)
    Organizer.objects.create(
        user=user,
        organizer_name='Test Organizer',
        organizer_email='testorg@example.com',
        created_by=user,
        is_active=True
    )
    return user


@pytest.fixture
def sample_event(db, organizer_user):
    organizer = organizer_user.organizers.first()
    event = Event.objects.create(
        organizer=organizer,
        name='Tech Conference 2025',
        description='A test tech conference',
        date=timezone.now() + timezone.timedelta(days=10),
        location='Bangalore',
        is_published=True,
        is_active=True
    )
    TicketType.objects.create(
        event=event,
        name='VIP Ticket',
        price=500.00,
        quantity_available=10,
        stripe_price_id='price_vip_test'
    )
    return event


@pytest.mark.django_db
def test_create_event_redirects_without_organizer_profile(client, attendee_user):
    client.force_login(attendee_user)
    url = reverse('create-event')
    response = client.get(url)
    # Should redirect to organizer-create
    assert response.status_code == 302
    assert reverse('organizer-create') in response.url


@pytest.mark.django_db
def test_create_event_accessible_with_organizer_profile(client, organizer_user):
    client.force_login(organizer_user)
    url = reverse('create-event')
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_ticket_preview_without_qr_code_does_not_crash(client, attendee_user, sample_event):
    client.force_login(attendee_user)
    rsvp = RSVP.objects.create(
        event=sample_event,
        attendee=attendee_user,
        ticket_qty=1,
        total_charge=500.00,
        is_active=True,
        transaction_id='test_txn_no_qr'
    )
    url = reverse('preview-ticket', kwargs={'rsvp_id': str(rsvp.id)})
    response = client.get(url)
    assert response.status_code == 200
    assert 'QR Code Generating...' in response.content.decode()
