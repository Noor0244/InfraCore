import os
import smtplib
from email.message import EmailMessage
from typing import Optional

class EmailSendError(Exception):
    pass

def send_email(to_email: str, subject: str, body: str, *, from_email: Optional[str] = None, from_name: Optional[str] = None) -> None:
    import logging
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = (os.getenv("SMTP_PASSWORD") or "").strip()
    sender_email = from_email or os.getenv("SMTP_FROM_EMAIL", username)
    sender_name = from_name or os.getenv("SMTP_FROM_NAME", "InfraCore Support")

    debug_msg = f"[SMTP DEBUG] send_email called. host={host}, port={port}, username={username}, sender_email={sender_email}, sender_name={sender_name}, to_email={to_email}"
    logging.warning(debug_msg)
    print(debug_msg)

    if not (host and port and username and password and sender_email):
        logging.error(f"[SMTP DEBUG] SMTP configuration is incomplete. host={host}, port={port}, username={username}, sender_email={sender_email}, sender_name={sender_name}")
        raise EmailSendError("SMTP configuration is incomplete.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to_email
    msg.set_content(body)

    try:
        logging.warning("[SMTP DEBUG] Connecting to SMTP server...")
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            logging.warning("[SMTP DEBUG] Calling STARTTLS...")
            smtp.starttls()
            smtp.ehlo()
            logging.warning("[SMTP DEBUG] STARTTLS complete. Logging in...")
            smtp.login(username, password)
            logging.warning("[SMTP DEBUG] Login successful. Sending email...")
            smtp.send_message(msg)
            logging.warning("[SMTP DEBUG] Email sent successfully.")
    except smtplib.SMTPAuthenticationError as e:
        logging.error("[SMTP DEBUG] SMTP authentication failed.")
        print("[SMTP DEBUG] SMTP authentication failed.")
        raise EmailSendError("SMTP authentication failed.") from e
    except smtplib.SMTPException as e:
        logging.error(f"[SMTP DEBUG] SMTP error: {e}")
        print(f"[SMTP DEBUG] SMTP error: {e}")
        raise EmailSendError(f"SMTP error: {e}") from e
    except Exception as e:
        logging.error(f"[SMTP DEBUG] Email send failed: {e}")
        print(f"[SMTP DEBUG] Email send failed: {e}")
        raise EmailSendError(f"Email send failed: {e}") from e
