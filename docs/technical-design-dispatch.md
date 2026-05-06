# Technical Design: Scream Sheet Dispatch

**PRD:** [prd-screamsheet-dispatch.md](prd-screamsheet-dispatch.md)

## Overview

This document describes the technical approach for the `screamsheet-dispatch` system — a Python cron-driven pipeline that syncs subscriber configs from Google Sheets, invokes the `screamsheet` generator per subscriber, delivers PDFs via SMTP, and logs the full run. The system is a new standalone repo with no shared code dependencies on `screamsheet`; it communicates with the generator as a subprocess via a defined config file contract.

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Workload type | Single-process Python script, cron-invoked | No concurrency needed at initial scale; simpler to debug and audit than a queue or daemon |
| Generator invocation | Subprocess call to `uv run screamsheet --config <path>` | Keeps repos decoupled; dispatch doesn't import screamsheet internals |
| Subscriber config storage | GUID-named YAML files in a local clone of a private GitHub repo | Three-tier replication (Google Sheet → local clone → GitHub); offsite backup on every sync run; no subscriber data lives inside the dispatch code repo |
| Subscriber source of truth | Google Sheets via Google Sheets API | Already chosen as the subscriber intake mechanism |
| Delivery | Python `smtplib` via Hostinger SMTP relay | Simple, no external dependencies; credentials stored in environment variables |
| Delivery logging | SQLite database | Lightweight persistence; no server required; easy to query for per-subscriber history |
| Run log | Plain text log file per run, plus end-of-run summary email | Log files provide permanent audit trail; summary email gives immediate visibility |
| Configuration | Single YAML config file (`dispatch_config.yaml`) | All tunable values in one place; no magic numbers in code |
| Rate limiting | Configurable per-email delay (sleep between sends) | Simple and effective at initial scale; avoids Hostinger SMTP quota |
| Team identification in subscriber configs | Store canonical team names only — no numeric IDs | IDs are generator-domain knowledge; dispatch and the signup form only deal in human-readable names; the generator resolves names to IDs via its own SQLite tables |

---

## Design Decisions (detail)

### Entry Point Script

A single script `run_dispatch.py` (invoked via `uv run screamsheet-dispatch`) orchestrates the full cycle in sequence:

1. Run sync (Google Sheets → local YAML configs → git commit + push to GitHub)
2. Run generator for each subscriber config
3. Run emailer for each subscriber outbox folder
4. Write run log to `logs/`
5. Send run summary email to admin

Each phase is isolated — a failure in one subscriber's generation does not stop the loop.

### Config Store

Subscriber YAML configs are stored in a **dedicated private GitHub repo**, cloned to a path on the server defined by `paths.config_store` in `dispatch_config.yaml`. The example config file (`dispatch_config.yaml.example`) will suggest a default of `/home/peter/Data/screamsheet-configs/`. This repo is entirely separate from the `screamsheet-dispatch` code repo — it contains only subscriber config files and receives no code changes.

This gives three tiers of subscriber data:
1. **Google Sheet** — source of truth; populated by the subscriber signup form
2. **Local clone** — working copy on the server; what the runner reads at generation time
3. **GitHub private repo** — offsite backup; always reflects the state after the last successful sync

The config store repo is initialized once at deployment time. The dispatch system never creates or clones the repo — it assumes the clone already exists at `paths.config_store`.

### Sync Module

The sync module calls the Google Sheets API, reads the subscriber sheet row by row, validates each row structurally (required fields present, types correct), and writes one YAML file per subscriber to the config store directory. Semantic validation (e.g. is the city real?) is not performed — that's left to the generator. After writing, changes are committed and pushed via `git add . && git commit && git push` subprocess calls.

If the `git push` fails, the failure is logged as a warning but the run continues — the local commit still serves as a fallback. If the Google Sheets API call fails entirely, the sync module returns a `SyncResult` indicating failure, the run continues using the existing config files (local clone), and the failure is recorded in the run log.

### Generator Invocation

For each subscriber config file, dispatch calls:

```
uv run screamsheet --config <path-to-subscriber-yaml> --output-dir <outbox/{date}/{guid}/>
```

The generator writes PDFs to `output_dir` and prints a JSON-serialized `list[GenerationResult]` to stdout. Dispatch reads stdout, parses the results, and records any layout warnings in the run log. If the subprocess exits non-zero or stdout cannot be parsed, that subscriber is marked as a generation failure.

### Outbox Structure

```
outbox/
  20260506/
    {guid}/
      nhl_20260506.pdf
      mlb_20260506.pdf
  20260507/
    {guid}/
      ...
```

At the start of each run, folders older than `retention_days` (from config) are deleted.

### Delivery

The emailer iterates the current day's outbox. For each subscriber folder it:
1. Reads the subscriber's email address from their config file (GUID maps to file).
2. Builds a `MIMEMultipart` email with all PDFs in the folder as attachments.
3. Sends via `smtplib.SMTP_SSL` using credentials from environment variables.
4. Logs the outcome to SQLite.

SMTP credentials (`DISPATCH_SMTP_HOST`, `DISPATCH_SMTP_USER`, `DISPATCH_SMTP_PASSWORD`) are read from environment variables, never from the config file.

### Run Log and Admin Alert

The run log is a structured plain-text file written to `logs/{YYYYMMDD_HHMMSS}.log`. It records:
- Sync outcome
- Per-subscriber: generation results, layout warnings, delivery outcome
- Any errors at any phase

At the end of the run, the log is emailed to the configured admin address as the email body (not an attachment, so it's readable on mobile). The admin email address is in `dispatch_config.yaml`.

---

## Interfaces

### dispatch_config.yaml

```
smtp:
  host: str                        — Hostinger SMTP hostname
  port: int                        — SMTP port (e.g. 465 for SSL)
  from_address: str                — e.g. peter@distractedfortune.com
  send_delay_seconds: float        — delay between subscriber emails

admin:
  alert_email: str                 — address that receives run summary emails

google_sheets:
  spreadsheet_id: str              — ID of the subscriber Google Sheet
  credentials_file: str            — path to Google service account JSON key

paths:
  config_store: str                — path to the local clone of the private subscriber config repo
  outbox: str                      — path to the outbox root directory

retention:
  outbox_days: int                 — days to keep outbox folders (default: 7)
```

### SyncResult

```
SyncResult:
  success: bool
  subscribers_updated: int
  subscribers_removed: int
  error: str | None               — populated on API failure
  used_fallback: bool             — True if existing configs were used due to failure
```

### RunResult (end-of-run summary)

```
RunResult:
  date: str
  sync: SyncResult
  subscribers: list[SubscriberRunResult]

SubscriberRunResult:
  guid: str
  name: str
  generation_success: bool
  generation_issues: list[str]    — layout/data warnings from GenerationResult
  delivery_success: bool
  delivery_error: str | None
```

### Generator CLI Contract

The `screamsheet` generator is invoked as a subprocess. Dispatch depends on this interface:

```
Command:
  uv run screamsheet --config <subscriber_yaml_path> --output-dir <output_dir>

Stdout:
  JSON array of GenerationResult objects:
  [
    {
      "pdf_path": "/path/to/nhl_20260506.pdf",
      "sheet_type": "nhl",
      "layout_clean": true,
      "issues": []
    },
    ...
  ]

Exit code:
  0  — all sheets attempted (even if some have layout warnings)
  1  — hard failure (could not read config, unhandled exception)
```

---

## Data Models

### SQLite Delivery Log (`dispatch.db`)

```
delivery_log:
  id             INTEGER PRIMARY KEY
  run_date       TEXT       — YYYYMMDD
  guid           TEXT       — subscriber GUID
  sheet_type     TEXT       — e.g. "nhl"
  pdf_path       TEXT
  email_address  TEXT
  outcome        TEXT       — "success" | "failure"
  error_detail   TEXT       — NULL on success
  timestamp      TEXT       — ISO 8601
```

---

## Integration Points

- **Google Sheets API** — OAuth2 service account credentials; reads one sheet (subscriber list). Dispatch does not write to the sheet.
- **`screamsheet` generator** — invoked as a `uv run` subprocess; communicates via the CLI contract defined above. No Python imports between repos.
- **Hostinger SMTP** — `smtplib.SMTP_SSL`; credentials via environment variables.
- **Git** — `subprocess` calls to `git add`, `git commit`, and `git push` in the config store directory. Git must be installed on the host, the config store directory must be a git repo, and push credentials (SSH key or personal access token) must be configured for the private GitHub remote.

---

## Open Questions

1. **Google Sheets service account setup** — Where is the service account JSON key stored, and how is it provisioned on the Linux server? This is a deployment question but affects the `credentials_file` config path. Needs to be answered before implementation.

2. **`uv` availability in cron context** — Cron jobs run with a minimal `PATH`. Does `uv` need to be specified by absolute path in the cron entry, or will the environment be set up to include it? Affects how the entry-point script is invoked.

3. **Config store git identity and push credentials** — The daily git commit+push needs a git user name, email, and push credentials configured on the server (SSH key or personal access token for the private GitHub repo). These are deployment prerequisites — does a git identity already exist on the server, and what auth method will be used for GitHub push?

4. **Hostinger SMTP rate limit** — The exact per-hour or per-day send limit for the Hostinger account is not yet known. The `send_delay_seconds` config knob handles this, but the right default value needs to be determined before going live.

---

## Out of Scope

- **Subscriber weather opt-in** — Weather on subscriber news sheets is suppressed for this release (`include_weather: false` in subscriber config). Enabling per-subscriber weather requires a geocoding integration to resolve city/state → lat/lon, which is deferred to a near-future update. When implemented, the signup form will collect city/state, dispatch will resolve coordinates via a geocoding API at sync time, and store them in the subscriber config for the generator to consume.
