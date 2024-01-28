from celery import shared_task

from communication.models import Notification

from .choices import ENGAGEMENT_TYPES


@shared_task
def platform_registration_notification(recipients: list[object] = None):
    try:
        if not recipients:
            raise ValueError("Recipients list is empty.")

        notification_type = ENGAGEMENT_TYPES[0][0]
        message = "Welcome to EventFlow! Your journey begins now. Explore the platform and make every event memorable."

        for recipient in recipients:
            obj = Notification.objects.create(
                user=recipient,
                message=message,
                notification_type=notification_type,
            )
    except Exception as e:
        return f"Error {platform_registration_notification.__name__ } sending notification: {e}"


@shared_task
def rsvp_registration_user_notification(recipients: list[object] = None):
    try:
        if not recipients:
            raise ValueError("Recipients list is empty.")

        notification_type = ENGAGEMENT_TYPES[1][0]
        message = "Exciting News! Your RSVP for an exclusive event is confirmed. Get ready for an unforgettable experience."

        for recipient in recipients:
            obj = Notification.objects.create(
                user=recipient,
                message=message,
                notification_type=notification_type,
            )
    except Exception as e:
        return f"Error {rsvp_registration_user_notification.__name__ } sending notification: {e}"


@shared_task
def rsvp_registration_organization_notification(
    recipients: list[object] = None,
):
    try:
        if not recipients:
            raise ValueError("Recipients list is empty.")

        notification_type = ENGAGEMENT_TYPES[2][0]
        message = "Exciting News! Your RSVP for an exclusive event is confirmed. Get ready for an unforgettable experience."

        for recipient in recipients:
            obj = Notification.objects.create(
                user=recipient,
                message=message,
                notification_type=notification_type,
            )
    except Exception as e:
        return f"Error {rsvp_registration_organization_notification.__name__ } sending notification: {e}"
