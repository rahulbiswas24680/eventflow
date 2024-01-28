from celery import shared_task
from django.template.loader import render_to_string

from .utils import send_email


@shared_task
def platform_registration_mail(user_name: str, recipients: list = None):
    try:
        subject = "Welcome Aboard! Unleash the Power of EventFlow"
        message = "Congratulations on joining EventFlow! Your journey to seamless event management starts here. Dive into the world of endless possibilities."
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string(
            "email/platform_registration.html", context
        )
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return (
            f"Error {platform_registration_mail.__name__ } sending email: {e}"
        )


@shared_task
def rsvp_registration_user_mail(user_name: str, recipients: list = None):
    try:
        subject = "You're Invited! RSVP to Exclusive Events"
        message = "Get ready for an exclusive event experience! Your RSVP has been received. Join the excitement and make every event memorable."
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string(
            "email/rsvp_registration_user.html", context
        )
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return (
            f"Error {rsvp_registration_user_mail.__name__} sending email: {e}"
        )


@shared_task
def rsvp_registration_organization_mail(
    user_name: str, recipients: list = None
):
    try:
        subject = "EventFlow: Expand Your Reach with RSVP Registrations"
        message = "Your organization is set to make waves! People are excited to RSVP to your upcoming events. Maximize your impact with EventFlow."
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string(
            "email/rsvp_registration_organization.html", context
        )
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return f"Error {rsvp_registration_organization_mail.__name__} sending email: {e}"


@shared_task
def ongoing_events_mail(user_name: str, recipients: list = None):
    try:
        subject = "Don't Miss Out! Explore Ongoing Events on EventFlow"
        message = "Stay in the loop with ongoing events. Your presence can add a spark to these dynamic experiences. Join now and make every moment count!"
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string("email/ongoing_events.html", context)
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return f"Error {ongoing_events_mail.__name__ } sending email: {e}"


@shared_task
def ticket_payment_user_mail(user_name: str, recipients: list = None):
    try:
        subject = "Success! Your Ticket Payment is Confirmed"
        message = "Celebrate the joy of success! Your ticket payment is confirmed. Get ready for an incredible event. Thank you for choosing EventFlow."
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string(
            "email/ticket_payment_user.html", context
        )
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return f"Error {ticket_payment_user_mail.__name__} sending email: {e}"


@shared_task
def ticket_payment_organization_mail(user_name: str, recipients: list = None):
    try:
        subject = "Great News! Tickets Sold Successfully for Your Event"
        message = "Cheers to success! Your event tickets have been sold successfully. Expect a vibrant crowd and unforgettable moments."
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string(
            "email/ticket_payment_organization.html", context
        )
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return f"Error {ticket_payment_organization_mail.__name__} sending email: {e}"


@shared_task
def event_announcements_mail(user_name: str, recipients: list = None):
    try:
        subject = "Big Announcements Await! Stay Tuned with EventFlow"
        message = "Exciting news is on the horizon! EventFlow is buzzing with upcoming announcements. Keep your eyes peeled for the latest updates."
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string(
            "email/event_announcements.html", context
        )
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return f"Error {event_announcements_mail.__name__} sending email: {e}"


@shared_task
def event_completion_user_mail(user_name: str, recipients: list = None):
    try:
        subject = "Congratulations! You've Successfully Completed an Event"
        message = "Kudos! You've successfully completed an event on EventFlow. Your active participation adds immense value. Keep shining!"
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string(
            "email/event_completion_user.html", context
        )
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return (
            f"Error {event_completion_user_mail.__name__} sending email: {e}"
        )


@shared_task
def event_completion_organization_mail(
    user_name: str, recipients: list = None
):
    try:
        subject = "Event Success! Your Organization's Achievement on EventFlow"
        message = "Your organization's event on EventFlow was a hit! Congratulations on a successful event. Your impact resonates far and wide."
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string(
            "email/event_completion_organization.html", context
        )
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return f"Error {event_completion_organization_mail.__name__} sending email: {e}"


@shared_task
def free_events_user_mail(user_name: str, recipients: list = None):
    try:
        subject = "Exclusive Access: Join Exciting Free Events on EventFlow"
        message = "Unlock exclusive access to thrilling free events. Dive into the world of entertainment without any barriers. Your journey begins now!"
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string("email/free_events_user.html", context)
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return f"Error {free_events_user_mail.__name__} sending email: {e}"


@shared_task
def organization_payment_event_mail(user_name: str, recipients: list = None):
    try:
        subject = "Payment Received! Your Event on EventFlow is Set to Thrive"
        message = "Success! Payments for your organization's event are confirmed. Witness the magic unfold as your event takes center stage."
        to = recipients

        context = {
            "user_name": user_name,
            "subject": subject,
            "message": message,
        }

        html_message = render_to_string(
            "email/organization_payment_event.html", context
        )
        send_email(subject, message, to, html_message=html_message)
    except Exception as e:
        return f"Error {organization_payment_event_mail.__name__} sending email: {e}"
