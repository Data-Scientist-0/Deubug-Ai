import smtplib
import os
from pathlib import Path
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Find .env from project root (2 levels up from this file)
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env", override=True)


def send_otp_email(to_email: str, username: str, otp_code: str) -> tuple[bool, str]:
    # Read fresh every call — never stale
    gmail_user     = os.getenv("GMAIL_USER", "").strip()
    gmail_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not gmail_user or not gmail_password:
        return False, (
            "Email credentials not configured. "
            "Open your .env file and make sure GMAIL_USER and GMAIL_APP_PASSWORD are set correctly."
        )

    subject = "DebugAI — Your Verification Code"

    html_body = f"""
    <html>
    <body style="font-family:Arial,sans-serif;background:#0a0f1e;color:#d0e8ff;padding:40px;">
        <div style="max-width:480px;margin:0 auto;background:#111827;border-radius:16px;
                    border:1px solid rgba(127,119,221,0.4);padding:32px;">
            <h1 style="color:#a0c4ff;font-size:24px;margin-bottom:4px;">🤖 DebugAI</h1>
            <p style="color:#6b7280;font-size:13px;margin-top:0;">AI/ML Code Debugging Agent</p>
            <hr style="border:none;border-top:1px solid rgba(127,119,221,0.2);margin:24px 0;">
            <p style="color:#d0e8ff;font-size:15px;">Hi <strong>{username}</strong>,</p>
            <p style="color:#9ca3af;font-size:14px;line-height:1.6;">
                Welcome to DebugAI! Use the code below to verify your email and activate your account.
            </p>
            <div style="background:#1f2937;border:1px solid rgba(127,119,221,0.5);
                        border-radius:12px;padding:24px;text-align:center;margin:24px 0;">
                <p style="color:#6b7280;font-size:12px;margin:0 0 8px;">Your verification code</p>
                <p style="color:#c0b8ff;font-size:40px;font-weight:700;
                           letter-spacing:12px;margin:0;font-family:monospace;">
                    {otp_code}
                </p>
                <p style="color:#6b7280;font-size:12px;margin:8px 0 0;">
                    Expires in <strong>10 minutes</strong>
                </p>
            </div>
            <p style="color:#6b7280;font-size:12px;line-height:1.6;">
                If you did not create an account on DebugAI, you can safely ignore this email.
            </p>
            <hr style="border:none;border-top:1px solid rgba(127,119,221,0.2);margin:24px 0;">
            <p style="color:#374151;font-size:11px;text-align:center;">
                DebugAI — AI/ML Code Debugging Agent
            </p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
DebugAI — Email Verification

Hi {username},

Your verification code is: {otp_code}

This code expires in 10 minutes.

If you did not sign up for DebugAI, ignore this email.
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"DebugAI <{gmail_user}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())

        return True, f"Verification code sent to {to_email}"

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Gmail authentication failed. "
            "Make sure you are using a Gmail App Password — not your regular Gmail password. "
            "Go to myaccount.google.com → Security → 2-Step Verification → App passwords."
        )
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"