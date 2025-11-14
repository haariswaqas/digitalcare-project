# api/tasks/EmailTask.py
import os
import resend

def send_email_task(subject, message, recipient_list, from_email=None):
    from_email = from_email or "onboarding@resend.dev"
    
    # Set the API key
    resend.api_key = os.environ.get("RESEND_API_KEY")
    
    try:
        for recipient in recipient_list:
            params = {
                "from": from_email,
                "to": [recipient],
                "subject": subject,
                "html": f"<p>{message}</p>",
            }
            email = resend.Emails.send(params)
            print(f"Email sent to {recipient}: {email}")
    except Exception as e:
        print(f"Error sending email: {e}")
        raise  # Re-raise to see full error during debugging