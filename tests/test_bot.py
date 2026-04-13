"""
Unit tests for LinkedIn Alert Bot modules.
Run: pytest tests/ -v
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch, mock_open
from src.config_loader import load_app_config, load_companies_config
from src.alert_creator import AlertResult
from src.reporter import RunReporter
from src.otp_fetcher import GmailOTPFetcher


# ─────────────────────────────────────────────
# Config Loader Tests
# ─────────────────────────────────────────────

class TestConfigLoader:
    def test_load_companies_config(self, tmp_path):
        data = {
            "job_title": "Data Engineer",
            "locations": {
                "London, United Kingdom": ["Google", "Amazon"],
                "Berlin, Germany": ["Zalando"]
            }
        }
        config_file = tmp_path / "companies.json"
        config_file.write_text(json.dumps(data))

        config = load_companies_config(str(config_file))
        assert config.job_title == "Data Engineer"
        assert "Google" in config.locations["London, United Kingdom"]
        assert len(config.locations) == 2

    def test_empty_location_allowed(self, tmp_path):
        data = {
            "job_title": "Data Engineer",
            "locations": {"Australia": []}
        }
        config_file = tmp_path / "companies.json"
        config_file.write_text(json.dumps(data))

        config = load_companies_config(str(config_file))
        assert config.locations["Australia"] == []


# ─────────────────────────────────────────────
# AlertResult Tests
# ─────────────────────────────────────────────

class TestAlertResult:
    def test_success_result(self):
        r = AlertResult(company="Google", location="London", status="success")
        assert r.status == "success"
        assert r.reason == ""

    def test_failed_result_with_reason(self):
        r = AlertResult(
            company="Zalando", location="Berlin", status="failed",
            reason="Company filter not found"
        )
        assert r.status == "failed"
        assert "filter" in r.reason


# ─────────────────────────────────────────────
# Reporter Tests
# ─────────────────────────────────────────────

class TestRunReporter:
    def _make_results(self):
        return [
            AlertResult("Google", "London", "success"),
            AlertResult("Amazon", "London", "success"),
            AlertResult("Zalando", "Berlin", "failed", "Timeout"),
        ]

    def test_report_counts(self, tmp_path):
        from src.config_loader import NotificationConfig
        notif = NotificationConfig(
            enabled=False, smtp_host="", smtp_port=587,
            sender_email="", sender_password="", recipient_email=""
        )
        reporter = RunReporter(self._make_results(), notif)
        success = [r for r in reporter.results if r.status == "success"]
        failed = [r for r in reporter.results if r.status == "failed"]
        assert len(success) == 2
        assert len(failed) == 1

    def test_save_report_creates_file(self, tmp_path):
        from src.config_loader import NotificationConfig
        notif = NotificationConfig(
            enabled=False, smtp_host="", smtp_port=587,
            sender_email="", sender_password="", recipient_email=""
        )
        reporter = RunReporter(self._make_results(), notif)
        output = str(tmp_path / "report.json")
        reporter.save_report(output)
        assert os.path.exists(output)

        with open(output) as f:
            data = json.load(f)
        assert data["success"] == 2
        assert data["failed"] == 1
        assert data["total"] == 3


# ─────────────────────────────────────────────
# OTP Fetcher Tests
# ─────────────────────────────────────────────

class TestGmailOTPFetcher:
    def test_otp_extraction_from_body(self):
        fetcher = GmailOTPFetcher("user@gmail.com", "apppass")
        body = "Your LinkedIn verification code is 847291. It expires in 15 minutes."
        import re
        match = re.search(r"\b(\d{6})\b", body)
        assert match is not None
        assert match.group(1) == "847291"

    def test_no_otp_in_body(self):
        fetcher = GmailOTPFetcher("user@gmail.com", "apppass")
        body = "Welcome to LinkedIn! Click here to confirm your account."
        import re
        match = re.search(r"\b(\d{6})\b", body)
        assert match is None
