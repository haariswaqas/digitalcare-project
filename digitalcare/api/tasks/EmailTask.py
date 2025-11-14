# api/tasks/EmailTask.py
import os
from resend import Resend  # note the capital R

# Create the Resend client with the API key from env vars
resend_client = Resend(api_key=os.environ.get("RESEND_API_KEY"))

def send_email_task(subject, message, recipient_list, from_email=None):
    from_email = from_email or "onboarding@resend.dev"
    try:
        for recipient in recipient_list:
            r = resend_client.emails.send(
                from_email=from_email,
                to=recipient,
                subject=subject,
                html=f"<p>{message}</p>",
            )
            print(f"Email sent to {recipient}: {r}")
    except Exception as e:
        print(f"Error sending email: {e}")
