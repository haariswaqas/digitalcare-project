# api/tasks/EmailTask.py
import os
import resend

# Load the Resend API key from environment variables
resend.api_key = os.environ.get("RESEND_API_KEY")

def send_email_task(subject, message, recipient_list, from_email=None):
    from_email = from_email or "onboarding@resend.dev"
    try:
        for recipient in recipient_list:
            r = resend.Emails.send({
                "from": from_email,
                "to": recipient,
                "subject": subject,
                "html": f"<p>{message}</p>",
            })
            print(f"Email sent to {recipient}: {r}")
    except Exception as e:
        print(f"Error sending email: {e}")
