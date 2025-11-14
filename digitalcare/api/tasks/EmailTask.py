# api/tasks.py
from django.core.mail import send_mail, EmailMessage
from django.conf import settings

def send_email_task(subject, message, recipient_list, from_email=None, fail_silently=False, attachments=None):
    print(f"Sending email to: {recipient_list}")
    from_email = from_email or settings.DEFAULT_FROM_EMAIL

    try:
        if attachments:
            email = EmailMessage(subject, message, from_email, recipient_list)
            for attachment in attachments:
                email.attach_file(attachment)
            email.send(fail_silently=fail_silently)
        else:
            send_mail(
                subject,
                message,
                from_email,
                recipient_list,
                fail_silently=fail_silently
            )

        print(f"Email sent successfully to: {recipient_list}")

    except Exception as e:
        print(f"Error sending email: {e}")
