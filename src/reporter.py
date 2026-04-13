import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from src.alert_creator import AlertResult
from src.config_loader import NotificationConfig
from src.logger import get_logger

logger = get_logger(__name__)


class RunReporter:
    """
    Aggregates alert results and generates a summary report.
    Optionally sends the report via email.
    """

    def __init__(self, results: list[AlertResult], notification_config: NotificationConfig):
        self.results = results
        self.config = notification_config
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def save_report(self, output_path: str = "logs/run_report.json") -> None:
        """Saves full run results as a JSON file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        report = {
            "run_timestamp": self.timestamp,
            "total": len(self.results),
            "success": sum(1 for r in self.results if r.status == "success"),
            "failed": sum(1 for r in self.results if r.status == "failed"),
            "skipped": sum(1 for r in self.results if r.status == "skipped"),
            "details": [
                {
                    "company": r.company,
                    "location": r.location,
                    "status": r.status,
                    "reason": r.reason
                }
                for r in self.results
            ]
        }
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Run report saved to: {output_path}")

    def print_summary(self) -> None:
        success = [r for r in self.results if r.status == "success"]
        failed = [r for r in self.results if r.status == "failed"]

        print("\n" + "=" * 60)
        print(f"  LinkedIn Job Alert Bot — Run Summary [{self.timestamp}]")
        print("=" * 60)
        print(f"  ✅ Successful : {len(success)}")
        print(f"  ❌ Failed     : {len(failed)}")
        print(f"  📦 Total      : {len(self.results)}")

        if failed:
            print("\n  Failed Companies:")
            for r in failed:
                print(f"    - {r.company} ({r.location}): {r.reason}")
        print("=" * 60 + "\n")

    def send_email_report(self) -> bool:
        """Sends the run summary as an HTML email."""
        if not self.config.enabled:
            logger.info("Email notifications disabled — skipping.")
            return False

        try:
            success = [r for r in self.results if r.status == "success"]
            failed = [r for r in self.results if r.status == "failed"]

            html = self._build_html_report(success, failed)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"LinkedIn Alert Bot Report — {self.timestamp}"
            msg["From"] = self.config.sender_email
            msg["To"] = self.config.recipient_email
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.sender_email, self.config.sender_password)
                server.sendmail(
                    self.config.sender_email,
                    self.config.recipient_email,
                    msg.as_string()
                )

            logger.info(f"Email report sent to: {self.config.recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email report: {e}")
            return False

    def _build_html_report(self, success, failed) -> str:
        success_rows = "".join(
            f"<tr><td>✅</td><td>{r.company}</td><td>{r.location}</td></tr>"
            for r in success
        )
        failed_rows = "".join(
            f"<tr><td>❌</td><td>{r.company}</td><td>{r.location}</td><td>{r.reason}</td></tr>"
            for r in failed
        )
        return f"""
        <html><body>
        <h2>LinkedIn Job Alert Bot — Run Report</h2>
        <p><strong>Run Time:</strong> {self.timestamp}</p>
        <p>✅ Success: <strong>{len(success)}</strong> &nbsp;|&nbsp;
           ❌ Failed: <strong>{len(failed)}</strong> &nbsp;|&nbsp;
           Total: <strong>{len(self.results)}</strong></p>

        <h3>Successful Alerts</h3>
        <table border="1" cellpadding="5">
            <tr><th>Status</th><th>Company</th><th>Location</th></tr>
            {success_rows}
        </table>

        <h3>Failed Alerts</h3>
        <table border="1" cellpadding="5">
            <tr><th>Status</th><th>Company</th><th>Location</th><th>Reason</th></tr>
            {failed_rows}
        </table>
        </body></html>
        """
