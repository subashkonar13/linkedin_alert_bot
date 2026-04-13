import json
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class NotificationConfig:
    enabled: bool
    smtp_host: str
    smtp_port: int
    sender_email: str
    sender_password: str
    recipient_email: str


@dataclass
class AppConfig:
    linkedin_email: str
    linkedin_password: str
    gmail_user: str
    gmail_app_password: str
    cookie_path: str
    alert_frequency: str
    headless: bool
    request_delay_seconds: int
    notification: NotificationConfig
    log_level: str


@dataclass
class CompaniesConfig:
    job_title: str
    locations: Dict[str, List[str]]


def load_app_config(path: str = "config/settings.json") -> AppConfig:
    with open(path) as f:
        data = json.load(f)
    notif = data.get("notification", {})
    return AppConfig(
        linkedin_email=data["linkedin_email"],
        linkedin_password=data["linkedin_password"],
        gmail_user=data.get("gmail_user", ""),
        gmail_app_password=data.get("gmail_app_password", ""),
        cookie_path=data.get("cookie_path", "config/cookies.json"),
        alert_frequency=data.get("alert_frequency", "Daily"),
        headless=data.get("headless", False),
        request_delay_seconds=data.get("request_delay_seconds", 4),
        notification=NotificationConfig(
            enabled=notif.get("enabled", False),
            smtp_host=notif.get("smtp_host", "smtp.gmail.com"),
            smtp_port=notif.get("smtp_port", 587),
            sender_email=notif.get("sender_email", ""),
            sender_password=notif.get("sender_password", ""),
            recipient_email=notif.get("recipient_email", "")
        ),
        log_level=data.get("log_level", "INFO")
    )


def load_companies_config(path: str = "config/companies.json") -> CompaniesConfig:
    with open(path) as f:
        data = json.load(f)
    return CompaniesConfig(
        job_title=data["job_title"],
        locations=data["locations"]
    )
