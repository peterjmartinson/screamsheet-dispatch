## Project Overview: The Scream Sheet Dispatcher

The **Scream Sheet Dispatcher** is a robust, automated delivery and orchestration layer designed to transition the "Scream Sheet" project from a personal automation tool into a scalable subscriber service. Following the principles of **Issue-Driven Development** and **TDD**, the Dispatcher acts as the connective tissue between a web-based "Source of Truth" and the final delivery to a user’s inbox.

### Core Architecture
The system operates on a **Sync-Process-Deliver** lifecycle:
1.  **Subscription Synchronization:** A nightly routine pulls data from a Google Sheet (the master record) and generates local, GUID-named YAML configuration files. These configs are version-controlled via Git to provide an audit trail and an "undo" button for data corruption.
2.  **Orchestrated Generation:** The Runner iterates through validated configs, triggering the `ReportLab` generator to build customized PDFs. To ensure high quality, the system utilizes **Platypus templates** for fluid layouts and `KeepTogether` containers for fixed sports charts. It dynamically manages overflow by intelligently compressing white space in preceding tables (like game scores) to protect the integrity of standings charts.
3.  **Fault-Tolerant Delivery:** Using the `peter@distractedfortune.com` SMTP relay, the Dispatcher sends the finalized PDFs. It employs a "send-what-we-have" philosophy—prioritizing delivery even if a sheet has formatting glitches—while logging errors to a local SQLite database and alerting the admin.

### Key Features
* **Dynamic Layout Control:** A layout-aware feedback loop that attempts deterministic retries to fit content onto a two-page "front and back" spread.
* **Rate-Limit Management:** A global configuration file defines wait times and quotas to stay within Hostinger’s SMTP limits.
* **Persistence & Cleanup:** The system maintains a seven-day rolling archive of generated folders for troubleshooting before automated deletion.
* **Validation Layer:** Strict schema enforcement during the sync process ensures that while the content (like a misspelled city) might fail at runtime, the system infrastructure remains stable and un-crashable.

This "walking skeleton" provides the foundation for a professional, branded news service capable of scaling from a single fan to thousands of sports and news enthusiasts.