import resend
from app.config import Config

resend.api_key = Config.RESEND_API_KEY


def send_audio_email(
    to_email:       str,
    recipient_name: str,
    loved_one_name: str,
    occasion_label: str,
    audio_url:      str,
) -> None:
    """
    Send the user an email with a link to the generated audio.
    The link is a signed Supabase URL valid for 7 days.
    """
    first = recipient_name.split()[0] if recipient_name else "there"

    resend.Emails.send({
        "from":    "Grief Companion <hello@yourdomain.com>",
        "to":      to_email,
        "subject": f"A message from {loved_one_name} — {occasion_label}",
        "html": f"""
        <div style="font-family:Georgia,serif;max-width:520px;margin:0 auto;
                    padding:40px 20px;color:#2c2c2a;">
          <p style="font-size:18px;margin-bottom:8px;">Dear {first},</p>
          <p style="font-size:15px;line-height:1.7;color:#5f5e5a;">
            Today is <strong>{occasion_label}</strong>.
            {loved_one_name} left something for you.
          </p>
          <div style="margin:32px 0;text-align:center;">
            <a href="{audio_url}"
               style="display:inline-block;background:#534AB7;color:white;
                      text-decoration:none;padding:14px 32px;
                      border-radius:8px;font-size:16px;">
              Listen to {loved_one_name}
            </a>
          </div>
          <p style="font-size:13px;color:#888780;">
            This link is valid for 7 days.
          </p>
        </div>
        """,
    })