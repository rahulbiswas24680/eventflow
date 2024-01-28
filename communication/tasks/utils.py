from django.core.mail import BadHeaderError, EmailMessage
from django.core.mail import EmailMessage, EmailMultiAlternatives

from django.utils.html import strip_tags
from django.conf import settings


def send_email(subject, message, to, from_email=None, cc=None, bcc=None, html_message=None):
    try:
        if html_message:
            # print('inside send email function')
            email = EmailMultiAlternatives(
                subject,
                strip_tags(message),
                from_email or settings.DEFAULT_FROM_EMAIL,
                to,
                cc=cc,
                bcc=bcc
            )
            email.attach_alternative(html_message, 'text/html')
        else:
            email = EmailMessage(
                subject,
                message,
                from_email or settings.DEFAULT_FROM_EMAIL,
                to,
                cc=cc,
                bcc=bcc
            )

        email.send()

    except BadHeaderError as e:
        raise str(e)

# ++++++++++++++++++++++++++++++++++++++++++ Example Usage ++++++++++++++++++++++++++++++++

# subject = 'Hello'
# message = 'Body of the email.'
# to = ['recipient@example.com']
# send_email(subject, message, to)

# # For HTML email
# html_message = render_to_string('email_template.html', {'variable': 'value'})
# send_email(subject, message, to, html_message=html_message)
