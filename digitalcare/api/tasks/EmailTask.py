# api/tasks.py
from resend import Resend
from django.conf import settings

resend_client = Resend(api_key=settings.RESEND_API_KEY)

def send_email_task(subject, message, recipient_list, from_email=None):
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    for recipient in recipient_list:
        try:
            resp = resend_client.emails.send(
                from_=from_email,
                to=recipient,
                subject=subject,
                text=message
            )
            print(f"Email sent to {recipient}, response id: {resp['id']}")
        except Exception as e:
            print(f"Error sending email to {recipient}: {e}")
