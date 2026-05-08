# Screamsheet Dispatch — Setup Checklist

Complete these steps in order before running `uv run screamsheet-dispatch` for the first time.

---

## 1. SMTP (Hostinger Email)

- [ ] Confirm the password for `peter@distractedfortune.com` in hPanel → Emails → Email Accounts
- [ ] Add to `.env` in the repo root:
  ```
  DISPATCH_SMTP_HOST=smtp.hostinger.com
  DISPATCH_SMTP_USER=peter@distractedfortune.com
  DISPATCH_SMTP_PASSWORD=your_email_password
  ```

---

## 2. Google Sheets API

- [ ] Go to [console.cloud.google.com](https://console.cloud.google.com)
- [ ] Create a project (or reuse an existing one)
- [ ] Enable the **Google Sheets API** for the project
- [ ] Create a **Service Account** (IAM & Admin → Service Accounts)
- [ ] Download the service account JSON key file
- [ ] Save the key file to a safe location (e.g. `/home/peter/Data/dispatch-credentials.json`)
- [ ] Open your Google Sheet → Share it with the service account's email address (read-only is fine)
- [ ] Note the Spreadsheet ID from the sheet URL: `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`

---

## 3. Google Sheet Structure

The sheet must have a header row with at least these columns:

| guid | name | email | sheets |
|------|------|-------|--------|
| some-unique-id | Alice Smith | alice@example.com | mlb,nhl |

- **guid** — a unique identifier per subscriber (used as the config filename)
- **name** — display name (used in logs)
- **email** — delivery address
- **sheets** — comma-separated list of sheet types: `nhl`, `mlb`, `nba`, `nfl`

---

## 4. Subscriber Config Format

Each subscriber YAML (auto-written by sync, or created manually for testing) looks like:

```yaml
name: Alice Smith
email: alice@example.com
mlb:
  favorite_teams:
    - name: Cubs
    - name: Cardinals
nhl:
  favorite_teams:
    - name: Blackhawks
```

Team names must match entries in the screamsheet database (populated by `uv run db_update` in the screamsheet repo).

---

## 5. Local Directories

- [ ] Create the config store directory:
  ```bash
  mkdir -p /home/peter/Data/screamsheet-configs
  ```
- [ ] Create the outbox directory:
  ```bash
  mkdir -p /home/peter/Data/screamsheet-outbox
  ```

---

## 6. `dispatch_config.yaml`

- [ ] Copy the example config:
  ```bash
  cp dispatch_config.yaml.example dispatch_config.yaml
  ```
- [ ] Edit `dispatch_config.yaml`:
  - Set `google_sheets.spreadsheet_id` to your Sheet ID
  - Set `google_sheets.credentials_file` to the path of your JSON key file
  - Set `paths.config_store` to `/home/peter/Data/screamsheet-configs/`
  - Set `paths.outbox` to `/home/peter/Data/screamsheet-outbox/`
  - Adjust `smtp.send_delay_seconds` if needed (default: 2.0 s between sends)

---

## 7. screamsheet Repo

The runner calls `uv run screamsheet-service` — it must be installed and working:

- [ ] Confirm it's installed: `cd ~/Code/screamsheet && uv run screamsheet-service --help`
- [ ] Run the DB update to populate team tables: `uv run db_update`

---

## 8. Test Run (no Google Sheets required)

To test generation + delivery without Google Sheets:

1. Skip sync by manually dropping a subscriber YAML into the config store:
   ```bash
   cp /path/to/test-subscriber.yaml /home/peter/Data/screamsheet-configs/test-sub.yaml
   ```
2. Run the dispatcher:
   ```bash
   cd ~/Code/screamsheet-dispatch
   uv run screamsheet-dispatch
   ```
3. Sync will fail → fall back to existing local configs → generation + delivery proceeds normally.
4. Check `/home/peter/Data/screamsheet-outbox/YYYYMMDD/` for output PDFs.
5. Check `logs/` for the run log.

---

## 9. Git for Config Audit Trail (optional)

`sync.py` runs `git add . && git commit && git push` after each sync to version-control subscriber configs.

- [ ] Initialize git in the config store: `git init /home/peter/Data/screamsheet-configs`
- [ ] Add a remote if you want off-machine backups: `git remote add origin <url>`
- [ ] If you skip this, sync will log a warning on the git step but continue.
