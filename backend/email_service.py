import smtplib
import os
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from dotenv import load_dotenv
    for p in [
        Path(__file__).resolve().parent.parent / ".env",
        Path(os.getcwd()) / ".env",
    ]:
        if p.exists():
            load_dotenv(dotenv_path=p, override=True)
            break
except Exception:
    pass


def send_otp_email(to_email: str, username: str, otp_code: str) -> tuple[bool, str]:
    gmail_user     = os.getenv("GMAIL_USER", "").strip()
    gmail_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    # Print to Railway logs so we can debug
    print(f"[EMAIL] Attempting to send to: {to_email}", flush=True)
    print(f"[EMAIL] From: {gmail_user}", flush=True)
    print(f"[EMAIL] Password set: {bool(gmail_password)}", flush=True)
    print(f"[EMAIL] Password length: {len(gmail_password)}", flush=True)

    if not gmail_user or not gmail_password:
        msg = "Email credentials not configured."
        print(f"[EMAIL ERROR] {msg}", flush=True)
        return False, msg

    subject   = "DebugAI — Your Verification Code"
    text_body = f"Hi {username},\n\nYour DebugAI verification code is: {otp_code}\n\nExpires in 10 minutes."
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0a0f1e;padding:40px;">
    <div style="max-width:480px;margin:0 auto;background:#111827;border-radius:16px;
                border:1px solid rgba(127,119,221,0.4);padding:32px;">
        <h1 style="color:#a0c4ff;">🤖 DebugAI</h1>
        <p style="color:#d0e8ff;">Hi <strong>{username}</strong>,</p>
        <p style="color:#9ca3af;">Your verification code is:</p>
        <div style="background:#1f2937;border-radius:12px;padding:24px;text-align:center;margin:24px 0;">
            <p style="color:#c0b8ff;font-size:40px;font-weight:700;letter-spacing:12px;
                       margin:0;font-family:monospace;">{otp_code}</p>
            <p style="color:#6b7280;font-size:12px;margin:8px 0 0;">Expires in 10 minutes</p>
        </div>
        <p style="color:#6b7280;font-size:12px;">If you did not sign up for DebugAI, ignore this email.</p>
    </div>
    </body></html>
    """

    try:
        print("[EMAIL] Connecting to smtp.gmail.com:587...", flush=True)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"DebugAI <{gmail_user}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            print("[EMAIL] Logging in...", flush=True)
            server.login(gmail_user, gmail_password)
            print("[EMAIL] Sending...", flush=True)
            server.sendmail(gmail_user, to_email, msg.as_string())

        print(f"[EMAIL] SUCCESS — sent to {to_email}", flush=True)
        return True, f"Verification code sent to {to_email}"

    except smtplib.SMTPAuthenticationError as e:
        msg = f"Gmail auth failed: {str(e)}. Use App Password not regular password."
        print(f"[EMAIL ERROR] {msg}", flush=True)
        return False, msg
    except smtplib.SMTPException as e:
        msg = f"SMTP error: {str(e)}"
        print(f"[EMAIL ERROR] {msg}", flush=True)
        return False, msg
    except Exception as e:
        msg = f"Email error: {type(e).__name__}: {str(e)}"
        print(f"[EMAIL ERROR] {msg}", flush=True)
        return False, msg
