# Bhakti Dhun daily automation

## Daily Windows schedule (India time, unless Windows uses another timezone)
- 09:00 — YouTube Short
- 12:00 — Long video
- 18:00 — YouTube Short
- 21:00 — YouTube Short

## Install
1. On the Windows PC, open the repository folder and pull the latest changes.
2. Confirm the virtual environment, API keys, and YouTube OAuth setup are working.
3. Run `install_automation.bat`. If task creation is denied, run it as administrator.
4. Keep the PC powered on and awake at the scheduled times.

Every run writes its own timestamped folder under `output/auto_...`; logs are saved under `logs/`. A video uploads only after rendering succeeds.

## Important YouTube visibility
The repository currently sets `VIDEO_PRIVACY = "unlisted"`. Uploading is automatic, but the videos will **not be publicly visible** unless that setting is deliberately changed to `"public"` in `config.py`. This setup uploads after rendering; it does not set a future scheduled publish time.

## Test before relying on unattended runs
Run one manual Short first:
```powershell
.\.venv\Scripts\python.exe scheduled_run.py --video-type shorts --slot test_short
```
Check the rendered video and the URL/status in `logs/`. Make sure YouTube OAuth is already authorized: if a token is missing or expired, the login flow may open a browser and unattended upload can fail.

## Remove automation
Run `uninstall_automation.bat`.
