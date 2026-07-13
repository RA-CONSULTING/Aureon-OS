# AUREON GRANT OPERATIONS SYSTEM v2.0
**Architecture Document**  
**Date:** 2026-07-03  
**Author:** Aureon Operations — Chief Grant Officer

---

## SYSTEM OVERVIEW

The expanded Aureon Grant Operations System integrates:
1. **Local Disk Watcher** — Monitors and indexes all research files
2. **Google Drive Sync** — Bidirectional sync with cloud storage
3. **Git Integration** — Auto-versioning of all grant documents
4. **Scraper Engine** — Automated collection of grant metadata and HNC/Gary mentions

## ARCHITECTURE

```
aureon-trading/
└── data/
    └── research/
        └── grants/
            ├── __init__.py
            ├── config.py                 # System configuration
            ├── core/
            │   ├── __init__.py
            │   ├── grant_tracker.py      # Main tracker (existing)
            │   ├── pipeline_manager.py   # Pipeline orchestration
            │   └── validator.py          # Data validation engine
            ├── integrations/
            │   ├── __init__.py
            │   ├── local_disk.py         # Local file watcher/indexer
            │   ├── google_drive.py       # GDrive OAuth + sync
            │   ├── git_manager.py        # Git auto-commit
            │   └── scraper_engine.py     # Web scrapers
            ├── scrapers/
            │   ├── __init__.py
            │   ├── ukri_scraper.py       # UKRI funding finder
            │   ├── innovateuk_scraper.py # Innovate UK scraper
            │   ├── ukspace_scraper.py    # UK Space Agency scraper
            │   ├── eu_scraper.py         # Horizon Europe scraper
            │   ├── us_scraper.py         # NIH/NSF/NASA scrapers
            │   ├── phil_scraper.py       # Philanthropic scrapers
            │   └── hnc_monitor.py        # HNC/Gary mention tracker
            ├── models/
            │   ├── __init__.py
            │   ├── opportunity.py        # Data models
            │   ├── application.py
            │   └── contact.py
            ├── utils/
            │   ├── __init__.py
            │   ├── logger.py             # Centralized logging
            │   ├── notifier.py           # Email/alert system
            │   └── scheduler.py          # Cron-like scheduling
            ├── tests/
            │   └── test_integrations.py
            ├── data/                     # Runtime data
            │   ├── cache/                # Scraper cache
            │   ├── index/                # File index
            │   └── logs/                 # System logs
            └── requirements.txt          # Python dependencies
```

## MODULES

### 1. Local Disk Integration (`local_disk.py`)
- **File Watcher:** Watch aureon repo for new/modified research files
- **Indexer:** Extract metadata (title, author, keywords, date) from PDFs, MDs, TXTs
- **Auto-classify:** Categorize files by research area (HNC, LSSP, PEFCφS, etc.)
- **Search:** Full-text search across all local research documents

### 2. Google Drive Integration (`google_drive.py`)
- **OAuth 2.0:** Authenticate with Gary's Google account
- **Sync:** Bidirectional sync between local `data/research/` and GDrive
- **Backup:** Automated daily backups of grant database
- **Shared Folders:** Access shared grant folders from collaborators

### 3. Git Integration (`git_manager.py`)
- **Auto-commit:** Commit grant database changes automatically
- **Versioning:** Track history of all grant applications
- **Branching:** Feature branches for major grant applications
- **Remote sync:** Push to GitHub/Bitbucket for team access

### 4. Scraper Engine (`scraper_engine.py`)
- **Grant Scrapers:** Monitor 20+ funding websites for new opportunities
- **HNC Monitor:** Track mentions of Harmonic Nexus Core across the web
- **Gary Monitor:** Track Gary Leckey's research impact and citations
- **Alert System:** Notify when new relevant opportunities appear

## WORKFLOW

```
1. Scraper Engine runs daily (06:00 UTC)
   → Fetches new grant opportunities
   → Monitors HNC/Gary mentions
   → Updates opportunities.json

2. Local Disk Watcher runs continuously
   → Detects new research files
   → Indexes and classifies
   → Updates file index

3. Git Manager runs on data changes
   → Auto-commits database updates
   → Tags major milestones
   → Pushes to remote

4. Google Drive syncs hourly
   → Uploads local changes
   → Downloads remote changes
   → Maintains consistency

5. Pipeline Manager generates weekly reports
   → New opportunities summary
   → Deadline alerts
   → Gary email digest
```

## CONFIGURATION

```python
# config.py
GRANT_CONFIG = {
    "local_disk": {
        "watch_paths": [
            "aureon-trading/data/research/",
            "aureon-trading/docs/",
            "aureon-trading/Kings_Accounting_Suite/"
        ],
        "file_types": [".md", ".txt", ".pdf", ".docx", ".py", ".json"],
        "index_interval_minutes": 60
    },
    "google_drive": {
        "sync_enabled": True,
        "local_root": "aureon-trading/data/research/",
        "drive_folder_id": None,  # Set after OAuth
        "sync_interval_hours": 1,
        "backup_enabled": True
    },
    "git": {
        "auto_commit": True,
        "commit_message_template": "[GRANT-OPS] {action}: {details}",
        "push_enabled": True,
        "remote_name": "origin",
        "branch": "main"
    },
    "scraper": {
        "enabled_sources": [
            "ukri", "innovate_uk", "uk_space", 
            "horizon_europe", "nasa", "nsf", "nih",
            "templeton", "simons", "schmidt", "cz_initiative"
        ],
        "hnc_monitor": {
            "keywords": ["Harmonic Nexus Core", "HNC", "Gary Leckey", "PEFCφS", "LSSP", "QGITA"],
            "sources": ["arxiv", "google_scholar", "researchgate", "academia_edu", "zenodo"]
        },
        "run_schedule": "0 6 * * *"  # Daily at 06:00 UTC
    },
    "notifications": {
        "email_enabled": True,
        "email_to": "gaxlec@gmail.com",
        "digest_frequency": "daily",
        "alert_on_deadline_days": 7
    }
}
```

## SECURITY

- All credentials stored in environment variables or encrypted config
- Google Drive OAuth tokens stored securely
- Git commits signed with GPG key
- No sensitive data in logs

---

*Aureon Operations — System Architecture v2.0*
