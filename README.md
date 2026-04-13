# LinkedIn Job Alert Bot

Automates job alert creation on LinkedIn for 150+ companies across 20+ global locations.
Handles 2FA via session cookies (primary) and Gmail OTP auto-fetch (fallback).

---

## Project Structure

```
linkedin_alert_bot/
├── config/
│   ├── companies.json        # All companies grouped by location
│   └── settings.json         # Credentials, delays, notification config
│   └── cookies.json          # Auto-generated after --setup run (do not commit)
├── src/
│   ├── __init__.py
│   ├── logger.py             # Centralised logging (console + file)
│   ├── config_loader.py      # Typed config dataclasses
│   ├── browser.py            # Chrome WebDriver factory
│   ├── otp_fetcher.py        # Gmail IMAP OTP extractor (2FA fallback)
│   ├── authenticator.py      # Login: cookies → credentials → manual
│   ├── alert_creator.py      # Core alert toggle logic per company
│   └── reporter.py           # Summary report + email notification
├── tests/
│   └── test_bot.py           # Unit tests (pytest)
├── logs/                     # Auto-created on first run
├── main.py                   # Entry point (CLI with flags)
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure `config/settings.json`
Fill in your LinkedIn email/password and (optionally) Gmail App Password
for automatic OTP handling.

To generate a Gmail App Password:
→ myaccount.google.com/apppasswords

### 3. First-time cookie setup (handles 2FA once)
```bash
python main.py --setup
```
A browser window opens. Log in manually and complete 2FA.
Cookies are saved automatically for all future runs.

---

## Usage

```bash
# Run all locations and companies
python main.py

# Run only a specific location
python main.py --location "London, United Kingdom"

# Preview companies without opening browser
python main.py --dry-run

# Dry run for one location
python main.py --dry-run --location "Berlin, Germany"

# Refresh cookies (when session expires)
python main.py --setup
```

---

## 2FA Handling Strategy

| Priority | Method             | When Used                          |
|----------|--------------------|------------------------------------|
| 1st      | Cookie session     | Every run after --setup            |
| 2nd      | Gmail OTP fetch    | When cookies expire                |
| 3rd      | Manual OTP wait    | If gmail_app_password not set      |

---

## Scheduling (Run Daily)

### Linux/macOS — crontab
```bash
# Runs every morning at 8:00 AM
0 8 * * * cd /path/to/linkedin_alert_bot && python main.py >> logs/cron.log 2>&1
```

### GitHub Actions (free cloud scheduling)
```yaml
# .github/workflows/alerts.yml
on:
  schedule:
    - cron: "0 8 * * *"
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          LINKEDIN_EMAIL: ${{ secrets.LINKEDIN_EMAIL }}
          LINKEDIN_PASSWORD: ${{ secrets.LINKEDIN_PASSWORD }}
```

---

## Covered Locations & Companies

| Location              | Companies |
|-----------------------|-----------|
| London, UK            | 38        |
| Berlin, Germany       | 51        |
| Amsterdam, Netherlands| 17        |
| Dublin, Ireland       | 11        |
| Luxembourg            | 1         |
| Glasgow, Scotland     | 1         |
| Warsaw, Poland        | 2         |
| Zurich, Switzerland   | 1         |
| Riga, Latvia          | 1         |
| Stockholm, Sweden     | 2         |
| Italy                 | 2         |
| Austria               | 1         |
| Paris, France         | 4         |
| Singapore             | 8         |
| Japan                 | 3         |
| Bangkok, Thailand     | 1         |
| South Africa          | 1         |
| Canada                | 7         |
| Spain                 | 5         |
| Estonia               | 2         |

**Total: ~160 company-location pairs**

---

## Important Notes

- LinkedIn's ToS restricts automated scraping — use for personal job search only.
- Add delays between requests (`request_delay_seconds` in settings) to avoid rate limits.
- LinkedIn's DOM changes periodically — XPath selectors in `alert_creator.py` may need updates.
- Never commit `config/cookies.json` or `config/settings.json` to version control.
- Add both to `.gitignore`.

---

## Running Tests

```bash
pytest tests/ -v
```
