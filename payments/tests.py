import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from events.models import Event, TicketType, RSVP
from payments.models import Transaction
from payments.tasks import process_checkout_session
from user_profiles.models import Organizer, Role
from unittest.mock import patch

User = get_user_model()


@pytest.fixture
def buyer_user(db):
    role, _ = Role.objects.get_or_create(name='attendee')
    user = User.objects.create_user(
        username='buyer_user',
        email='buyer@example.com',
        password='testpassword',
        current_role=role
    )
    user.available_roles.add(role)
    return user


@pytest.fixture
def ticket_event(db):
    role, _ = Role.objects.get_or_create(name='organizer')
    org_user = User.objects.create_user(
        username='event_host',
        email='host@example.com',
        password='testpassword',
        current_role=role
    )
    org_user.available_roles.add(role)
    organizer = Organizer.objects.create(
        user=org_user,
        organizer_name='Host Org',
        organizer_email='host@example.com',
        created_by=org_user,
        is_active=True
    )
    event = Event.objects.create(
        organizer=organizer,
        name='Exclusive Concert',
        description='Only limited tickets',
        date=timezone.now() + timezone.timedelta(days=5),
        location='Mumbai',
        is_published=True,
        is_active=True
    )
    ticket = TicketType.objects.create(
        event=event,
        name='Pass',
        price=100.00,
        quantity_available=5,
        stripe_price_id='price_pass_123'
    )
    return ticket


@pytest.mark.django_db
def test_pre_checkout_rejects_insufficient_stock(api_client, buyer_user, ticket_event):
    api_client.force_authenticate(user=buyer_user)
    url = reverse('ticket_payment')
    # Try requesting 10 tickets when only 5 are available
    payload = {
        'tickets': [{'ticket_id': ticket_event.id, 'quantity': 10}]
    }
    response = api_client.post(url, data=payload, format='json')
    assert response.status_code == 400
    assert 'Not enough tickets available' in response.data['error']


@pytest.mark.django_db
@patch('qr_codes.tasks.generate_qr_code.delay')
@patch('communication.tasks.mail_tasks.ticket_payment_user_mail.delay')
def test_process_checkout_session_atomically_decrements_inventory(
    mock_mail, mock_qr, buyer_user, ticket_event
):
    session_id = 'cs_test_session_abc'
    initial_qty = ticket_event.quantity_available
    purchased_qty = 2

    txn = Transaction.objects.create(
        user=buyer_user,
        ticket_type=ticket_event,
        currency='INR',
        amount=ticket_event.price,
        quantity=purchased_qty,
        payment_status='PENDING',
        session_id=session_id,
        transaction_id='pi_test_123'
    )

    result = process_checkout_session(session_id)
    assert result['status'] == 'success'
    assert result['processed'] == 1

    # Verify inventory was decremented accurately
    ticket_event.refresh_from_db()
    assert ticket_event.quantity_available == initial_qty - purchased_qty

    # Verify transaction and RSVP status
    txn.refresh_from_db()
    assert txn.payment_status == 'SUCCESS'
    assert txn.rsvp is not None
    assert txn.rsvp.is_active is True
    assert txn.rsvp.ticket_qty == purchased_qty


@pytest.mark.django_db
@patch('qr_codes.tasks.generate_qr_code.delay')
@patch('communication.tasks.mail_tasks.ticket_payment_user_mail.delay')
def test_process_checkout_session_fails_when_oversold(
    mock_mail, mock_qr, buyer_user, ticket_event
):
    session_id = 'cs_test_oversold'
    # Set available to 1, but transaction demands 2
    ticket_event.quantity_available = 1
    ticket_event.save()

    txn = Transaction.objects.create(
        user=buyer_user,
        ticket_type=ticket_event,
        currency='INR',
        amount=ticket_event.price,
        quantity=2,
        payment_status='PENDING',
        session_id=session_id,
        transaction_id='pi_test_oversold'
    )

    with pytest.raises(ValueError, match="Not enough tickets available"):
        process_checkout_session(session_id)

    # Quantity should remain untouched due to transaction atomic rollback
    ticket_event.refresh_from_db()
    assert ticket_event.quantity_available == 1
