import os
import json
import urllib.request
import urllib.error
from pathlib import Path

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
    api_key = os.getenv("RESEND_API_KEY", "").strip()

    print(f"[EMAIL] Sending to: {to_email}", flush=True)
    print(f"[EMAIL] API key set: {bool(api_key)}", flush=True)

    if not api_key:
        return False, "RESEND_API_KEY not configured. Add it to your environment variables."

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0a0f1e;padding:40px;">
    <div style="max-width:480px;margin:0 auto;background:#111827;border-radius:16px;
                border:1px solid rgba(127,119,221,0.4);padding:32px;">
        <h1 style="color:#a0c4ff;">🤖 DebugAI</h1>
        <p style="color:#d0e8ff;">Hi <strong>{username}</strong>,</p>
        <p style="color:#9ca3af;">Your verification code is:</p>
        <div style="background:#1f2937;border-radius:12px;padding:24px;
                    text-align:center;margin:24px 0;">
            <p style="color:#c0b8ff;font-size:40px;font-weight:700;
                       letter-spacing:12px;margin:0;font-family:monospace;">
                {otp_code}
            </p>
            <p style="color:#6b7280;font-size:12px;margin:8px 0 0;">
                Expires in 10 minutes
            </p>
        </div>
        <p style="color:#6b7280;font-size:12px;">
            If you did not sign up for DebugAI, ignore this email.
        </p>
    </div>
    </body></html>
    """

    payload = json.dumps({
        "from":    "DebugAI <onboarding@resend.dev>",
        "to":      [to_email],
        "subject": "DebugAI — Your Verification Code",
        "html":    html_body,
        "text":    f"Hi {username},\n\nYour DebugAI verification code is: {otp_code}\n\nExpires in 10 minutes.",
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )

    try:
        print("[EMAIL] Calling Resend API...", flush=True)
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            print(f"[EMAIL] SUCCESS: {result}", flush=True)
            return True, f"Verification code sent to {to_email}"

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[EMAIL ERROR] HTTP {e.code}: {body}", flush=True)
        return False, f"Email API error: {body}"
    except Exception as e:
        print(f"[EMAIL ERROR] {type(e).__name__}: {str(e)}", flush=True)
        return False, f"Email error: {str(e)}"
