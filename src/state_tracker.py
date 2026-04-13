"""
State Tracker — Persists which company+location alerts have already been set.
Prevents re-processing on re-runs and supports resumable execution.
"""

import json
import os
from datetime import datetime
from src.logger import get_logger

logger = get_logger(__name__)

STATE_FILE = "config/state.json"


class StateTracker:
    """
    Maintains a persistent record of alert statuses.
    Key format: "Company::Location"

    Statuses:
        "success"  — Alert was successfully set
        "failed"   — Last attempt failed (eligible for retry)
        "skipped"  — Intentionally skipped
    """

    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.state: dict = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                logger.info(f"State loaded: {len(data)} records from {self.state_file}")
                return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load state file: {e}. Starting fresh.")
        return {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def _key(self, company: str, location: str) -> str:
        return f"{company}::{location}"

    def is_done(self, company: str, location: str) -> bool:
        """Returns True if alert was already successfully set."""
        return self.state.get(self._key(company, location), {}).get("status") == "success"

    def mark(self, company: str, location: str, status: str, reason: str = "") -> None:
        """Record the result of an alert attempt."""
        self.state[self._key(company, location)] = {
            "status": status,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        self._save()

    def get_failed(self) -> list[tuple[str, str]]:
        """Returns list of (company, location) tuples that previously failed."""
        return [
            tuple(key.split("::", 1))
            for key, val in self.state.items()
            if val.get("status") == "failed"
        ]

    def summary(self) -> dict:
        statuses = [v["status"] for v in self.state.values()]
        return {
            "total_tracked": len(statuses),
            "success": statuses.count("success"),
            "failed": statuses.count("failed"),
            "skipped": statuses.count("skipped"),
        }

    def reset(self) -> None:
        """Clears all state — use when you want to re-run everything from scratch."""
        self.state = {}
        self._save()
        logger.info("State reset.")
