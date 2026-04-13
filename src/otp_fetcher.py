import imaplib
import email
import re
import time
from src.logger import get_logger

logger = get_logger(__name__)


class GmailOTPFetcher:
    """
    Fetches LinkedIn 2FA OTP from Gmail inbox using IMAP.

    Prerequisites:
    - Enable IMAP in Gmail settings.
    - Generate an App Password at: myaccount.google.com/apppasswords
      (Do NOT use your real Gmail password here.)
    """

    IMAP_HOST = "imap.gmail.com"
    LINKEDIN_SENDER = "security-noreply@linkedin.com"

    def __init__(self, gmail_user: str, gmail_app_password: str):
        self.gmail_user = gmail_user
        self.gmail_app_password = gmail_app_password

    def fetch_otp(self, retries: int = 6, wait_seconds: int = 5) -> str | None:
        """
        Polls Gmail for a LinkedIn OTP email and extracts the 6-digit code.

        Args:
            retries: Number of times to poll before giving up.
            wait_seconds: Seconds to wait between each poll.

        Returns:
            OTP string if found, else None.
        """
        logger.info("Polling Gmail for LinkedIn OTP...")

        for attempt in range(1, retries + 1):
            try:
                mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
                mail.login(self.gmail_user, self.gmail_app_password)
                mail.select("inbox")

                _, data = mail.search(
                    None,
                    f'(FROM "{self.LINKEDIN_SENDER}" UNSEEN)'
                )
                ids = data[0].split()

                if ids:
                    latest_id = ids[-1]
                    _, msg_data = mail.fetch(latest_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    body = self._extract_body(msg)
                    otp_match = re.search(r"\b(\d{6})\b", body)

                    if otp_match:
                        otp = otp_match.group(1)
                        logger.info(f"OTP retrieved successfully: {otp}")
                        mail.logout()
                        return otp

                logger.debug(f"OTP not found (attempt {attempt}/{retries}). Retrying in {wait_seconds}s...")
                mail.logout()
                time.sleep(wait_seconds)

            except Exception as e:
                logger.error(f"Gmail IMAP error on attempt {attempt}: {e}")
                time.sleep(wait_seconds)

        logger.error("Failed to retrieve OTP after all retries.")
        return None

    @staticmethod
    def _extract_body(msg) -> str:
        """Extracts plain text body from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    except Exception:
                        continue
        else:
            try:
                return msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except Exception:
                return ""
        return ""
