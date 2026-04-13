"""
LinkedIn Job Alert Bot — Main Entry Point

Usage:
    python main.py --setup              # One-time cookie save (handles 2FA)
    python main.py                      # Full run — all locations & companies
    python main.py --location "London, United Kingdom"
    python main.py --retry-failed       # Re-run only previously failed alerts
    python main.py --reset-state        # Clear all tracked state and start fresh
    python main.py --dry-run            # Preview companies without opening browser
    python main.py --status             # Show current state summary
"""

import argparse
import sys
from src.config_loader import load_app_config, load_companies_config
from src.browser import BrowserFactory
from src.otp_fetcher import GmailOTPFetcher
from src.authenticator import LinkedInAuthenticator
from src.orchestrator import AlertOrchestrator
from src.state_tracker import StateTracker
from src.reporter import RunReporter
from src.logger import get_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LinkedIn Job Alert Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--setup", action="store_true",
                        help="One-time cookie save via manual login")
    parser.add_argument("--location", type=str, default=None,
                        help="Process only a specific location")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Retry only previously failed alerts")
    parser.add_argument("--reset-state", action="store_true",
                        help="Clear state file and start from scratch")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview companies without opening browser")
    parser.add_argument("--status", action="store_true",
                        help="Show current alert state summary and exit")
    return parser.parse_args()


def show_status():
    tracker = StateTracker()
    summary = tracker.summary()
    failed = tracker.get_failed()
    print("\n===== Alert State Summary =====")
    print(f"  Total tracked : {summary['total_tracked']}")
    print(f"  Success       : {summary['success']}")
    print(f"  Failed        : {summary['failed']}")
    print(f"  Skipped       : {summary['skipped']}")
    if failed:
        print(f"\n  Failed entries ({len(failed)}):")
        for company, location in failed:
            print(f"    - {company} ({location})")
    print("================================\n")


def dry_run(companies_config, location_filter=None):
    tracker = StateTracker()
    print("\n DRY RUN — Companies to be processed:\n")
    total = pending = done = 0
    for location, companies in companies_config.locations.items():
        if location_filter and location != location_filter:
            continue
        if not companies:
            continue
        already_done = sum(1 for c in companies if tracker.is_done(c, location))
        remaining = len(companies) - already_done
        print(f"  {location}  ({remaining} pending / {already_done} done)")
        for c in companies:
            tick = "[done]" if tracker.is_done(c, location) else "[    ]"
            print(f"      {tick} {c}")
        total += len(companies)
        done += already_done
        pending += remaining
    print(f"\n  Total: {total} | Pending: {pending} | Done: {done}\n")


def main():
    args = parse_args()
    config = load_app_config()
    companies_config = load_companies_config()
    logger = get_logger("main", config.log_level)

    if args.status:
        show_status()
        return

    if args.reset_state:
        StateTracker().reset()
        logger.info("State cleared. Next run will process all companies.")
        return

    if args.dry_run:
        dry_run(companies_config, args.location)
        return

    driver = BrowserFactory.get_driver(headless=config.headless)

    try:
        otp_fetcher = GmailOTPFetcher(config.gmail_user, config.gmail_app_password) \
            if config.gmail_user else None

        auth = LinkedInAuthenticator(
            driver=driver,
            email=config.linkedin_email,
            password=config.linkedin_password,
            cookie_path=config.cookie_path,
            otp_fetcher=otp_fetcher
        )

        if args.setup:
            auth.save_cookies()
            logger.info("Setup complete. Run without --setup to start.")
            return

        logger.info("Logging into LinkedIn...")
        if not auth.login():
            logger.error("Login failed. Run --setup to refresh cookies.")
            sys.exit(1)

        orchestrator = AlertOrchestrator(
            driver=driver,
            companies_config=companies_config,
            delay_seconds=config.request_delay_seconds,
            max_retries=3,
            location_filter=args.location,
            retry_failed_only=args.retry_failed
        )

        all_results = orchestrator.run()

        reporter = RunReporter(all_results, config.notification)
        reporter.print_summary()
        reporter.save_report()

        if config.notification.enabled:
            reporter.send_email_report()

        show_status()

    finally:
        BrowserFactory.quit_driver(driver)


if __name__ == "__main__":
    main()
