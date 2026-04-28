import resend
from app.config import Config

resend.api_key = Config.RESEND_API_KEY


def send_weekly_email(
    to_email:       str,
    recipient_name: str,
    audio_url:      str,
    summary_text:   str,
) -> None:
    first = recipient_name.split()[0] if recipient_name else "there"

    resend.Emails.send({
        "from":    "MindEcho <hello@yourdomain.com>",
        "to":      to_email,
        "subject": "Your week in words — MindEcho weekly reflection",
        "html": f"""
        <div style="font-family:Georgia,serif;max-width:520px;margin:0 auto;
                    padding:40px 20px;color:#2c2c2a;">
          <p style="font-size:18px;margin-bottom:8px;">Hi {first},</p>
          <p style="font-size:15px;line-height:1.7;color:#5f5e5a;">
            Here is a reflection on your week — written just for you.
          </p>
          <div style="background:#f0eefc;border-radius:10px;padding:20px 24px;
                      margin:24px 0;font-style:italic;color:#3C3489;
                      font-size:14px;line-height:1.8;">
            {summary_text}
          </div>
          <div style="text-align:center;margin:32px 0;">
            <a href="{audio_url}"
               style="display:inline-block;background:#534AB7;color:white;
                      text-decoration:none;padding:14px 32px;
                      border-radius:8px;font-size:16px;">
              Listen to your reflection
            </a>
          </div>
          <p style="font-size:13px;color:#888780;">
            Audio link valid for 7 days. Keep journaling — every entry matters.
          </p>
        </div>
        """,
    })