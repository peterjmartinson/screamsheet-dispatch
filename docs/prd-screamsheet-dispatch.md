# PRD: Scream Sheet Dispatch

## Summary

The Scream Sheet Dispatch system automates the end-to-end delivery of personalized PDF "screamsheets" to subscribers. It pulls subscriber preferences from a Google Sheet, generates local config files for each subscriber, invokes the `screamsheet` PDF generator to produce their requested sheets, and delivers the results via email — every morning, without human intervention.

The problem it solves: the `screamsheet` generator currently produces PDFs for one user (the developer). This system extends it to any number of subscribers, each with their own preferences, without requiring manual work for each delivery. The dispatch system passes each subscriber's YAML config directly to the generator, which produces all of that subscriber's requested PDFs in a single invocation.

---

## Acceptance Criteria

### Subscription Sync

- [ ] **AC-SYNC-01** — The system reads subscriber data from a configured Google Sheet and produces one YAML config file per subscriber, named by the subscriber's GUID.
- [ ] **AC-SYNC-02** — Each config file contains the subscriber's GUID, name, email address, list of requested sheet types, and per-sheet options (e.g., preferred teams, weather location).
- [ ] **AC-SYNC-03** — Config files are always structurally valid YAML and parseable by the runner, regardless of what data the subscriber entered in the Google Sheet.
- [ ] **AC-SYNC-04** — If a subscriber row is removed from the Google Sheet, their config file is removed from the local config store on the next sync.
- [ ] **AC-SYNC-05** — Every sync run commits any changes to the config store to a local Git repository, creating a version-controlled audit trail.
- [ ] **AC-SYNC-06** — If the Google Sheets sync fails (API outage, expired credentials, network error), the runner falls back to the most recently committed set of config files and logs an alert to the admin.
- [ ] **AC-SYNC-07** — If a subscriber's config contains semantically invalid data (e.g., unrecognized sheet type, invalid location), the runner attempts generation anyway with that config and logs any resulting errors. If generation crashes entirely for that subscriber, they receive no email that day and the failure is logged and the admin is alerted.

### Runner / Generation

- [ ] **AC-RUN-01** — The runner iterates through all config files and, for each subscriber, invokes the `screamsheet` generator exactly once — passing the path to that subscriber's YAML config file. The generator produces all PDFs requested in the config in that single invocation.
- [ ] **AC-RUN-02** — Generated PDFs are placed in an outbox folder structured as `outbox/{YYYYMMDD}/{GUID}/`, one folder per subscriber per day.
- [ ] **AC-RUN-03** — If generation fails for one subscriber, the runner logs the failure, alerts the admin, and continues to the next subscriber without stopping.
- [ ] **AC-RUN-04** — If the generator's structured result includes layout warnings for any sheet, the runner records those warnings in the run log and still places the PDF in the subscriber's outbox folder for delivery.
- [ ] **AC-RUN-05** — The system provides a single entry-point script that executes the full sync-generate-deliver cycle in sequence, designed to be invoked by a cron job.

### Delivery

- [ ] **AC-DLVR-01** — After all PDFs are generated, the runner sends one email per subscriber containing all of their PDFs as attachments.
- [ ] **AC-DLVR-02** — Each email is sent from `peter@distractedfortune.com` with the subject line `Scream Sheet for {date}` and a brief boilerplate body listing the attached sheets.
- [ ] **AC-DLVR-03** — If sending fails for one subscriber (e.g., invalid email address, SMTP error), the runner logs the failure, alerts the admin, and continues to the next subscriber.
- [ ] **AC-DLVR-04** — Every delivery attempt (success or failure) is logged to a local SQLite database with the subscriber GUID, date, outcome, and any error detail.

### Logging & Alerting

- [ ] **AC-LOG-01** — The runner maintains a run log for each daily execution, capturing: sync outcome, per-subscriber generation results (including any generator warnings), and per-subscriber delivery outcome.
- [ ] **AC-LOG-02** — Run logs are saved to a `logs/` folder and retained permanently — they are never automatically deleted.
- [ ] **AC-LOG-03** — At the conclusion of each run, the full run log is emailed to a configured admin email address.
- [ ] **AC-LOG-04** — The admin alert email address is defined in configuration and not hardcoded.
- [ ] **AC-LOG-05** — "Alerts the admin" throughout this PRD means: record the event in the run log (AC-LOG-01) and ensure it is included in the end-of-run email (AC-LOG-03).

### Rate Limiting & Configuration

- [ ] **AC-CFG-01** — SMTP rate limits, retry counts, delivery wait times, the 7-day outbox archive retention period, and the admin alert email address are all defined in a global configuration file, not hardcoded.
- [ ] **AC-CFG-02** — The runner respects the configured per-email delay to stay within Hostinger's SMTP sending limits.

### Cleanup

- [ ] **AC-CLEAN-01** — At the start of each run, the outbox folder is scanned and any daily folders older than the configured retention period (default: 7 days) are deleted.

---

## Out of Scope

- PDF layout quality control and overflow handling — those changes belong in the `screamsheet` generator repo.
- Payment processing and subscription billing.
- A subscriber-facing web interface or self-service account management.
- Custom or user-defined sheet types not already supported by the `screamsheet` generator.
- Branding and visual design of the screamsheets themselves.
- Git repository initialization — the config store repo is assumed to be initialized as part of one-time deployment setup.
