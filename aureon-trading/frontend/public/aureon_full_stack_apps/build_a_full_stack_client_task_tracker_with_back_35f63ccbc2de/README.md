# Aureon Full-Stack System

Prompt: Build a full-stack client task tracker with backend API, frontend dashboard, local data store, tests, runbook, and browser preview proof.

## What The Agents Built
- `backend/server.py`: Python stdlib JSON API with health, list, and create endpoints.
- `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`: browser UI that can talk to the backend.
- `tests/test_contract.py`: local API contract proof.
- `metadata.json`: build evidence and run commands.

## Run Locally
```powershell
cd C:\Users\user\aureon-trading-integrated-main-20260508\frontend\public\aureon_full_stack_apps\build_a_full_stack_client_task_tracker_with_back_35f63ccbc2de
python backend/server.py --port 8787
```

Then open `/aureon_full_stack_apps/build_a_full_stack_client_task_tracker_with_back_35f63ccbc2de/frontend/index.html` from the Aureon console. The static preview still renders if the API is not running, and switches to live API mode when the backend is available.
