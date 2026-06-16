# Desk Booker — Comfy App Automation

Automatically books desk **7S.009** on [my.comfyapp.com](https://my.comfyapp.com) every weekday.
It logs in via your BP company SSO, searches for the desk, and books all available dates on the calendar in one go.

---

## How It Works

1. The script opens a headless (invisible) Chrome browser using **Playwright**
2. It loads your saved login session — no password prompt needed each time
3. It searches for desk `7S.009` using the search bar on the floor map
4. It clicks the **Book** button next to the desk in search results
5. It opens the calendar and clicks **all green (available) weekday dates**
   - Green = open for booking, Grey = not open yet, Checkmark = already booked
   - Weekends (Sat/Sun) are automatically skipped
   - On Monday, if Saturday and Sunday both unlocked new days, it books both at once
6. It clicks **Complete booking** to confirm
7. Windows Task Scheduler runs this automatically every **Mon–Fri at 12:00 PM**

---

## Files

| File | Purpose |
|------|---------|
| `book_desk.py` | Main automation script |
| `create_task.bat` | Registers the scheduled task (blocked by BP policy — use PowerShell instead) |
| `auth_state.json` | Your saved login session (auto-created on first login) |
| `booking_confirmation.png` | Screenshot of last booking result |
| `debug_screenshot.png` | Screenshot saved when something goes wrong |

---

## First-Time Setup (New User)

### Step 1 — Install Python
Download from https://www.python.org/downloads/ and install.
During install, check **"Add Python to PATH"**.

### Step 2 — Install Playwright
Open **PowerShell** and run:
```
pip install playwright
python -m playwright install chromium
```

### Step 3 — One-Time Login
Run this to save your SSO session:
```
python C:\Users\YOUR_USERNAME\Downloads\desk-booker\book_desk.py --login
```
A browser window will open. Click **"Sign in with your organization"** and complete your Microsoft/BP login.
Once you are fully logged in and see the Comfy app, come back to PowerShell and press **Enter**.
This saves your session to `auth_state.json` — future runs use this automatically.

### Step 4 — Test the Booking
Run without `--login` to do a test booking:
```
python C:\Users\YOUR_USERNAME\Downloads\desk-booker\book_desk.py
```
Check `booking_confirmation.png` in the desk-booker folder — it should show the booked dates highlighted in dark green.

### Step 5 — Set Up Auto-Schedule (via PowerShell)
> Note: `.bat` files are blocked by BP group policy, so use PowerShell directly.

Open PowerShell and run this single line (update YOUR_USERNAME):
```
schtasks /create /tn "ComfyDeskBooking" /tr "python C:\Users\YOUR_USERNAME\Downloads\desk-booker\book_desk.py" /sc WEEKLY /d MON,TUE,WED,THU,FRI /st 12:00 /f
```
You should see: `SUCCESS: The scheduled task "ComfyDeskBooking" has successfully been created.`

From now on the script runs automatically every **Mon–Fri at 12:00 PM** with no action needed from you.

---

## Changing the Desk

Open `book_desk.py` in Notepad and change this line near the top:
```python
DESK_NAME = "7s.009"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Session expired` error | Re-run Step 3 (`--login`) to refresh your session |
| Desk not found | Check `debug_screenshot.png` — search may have failed |
| No dates selected | Check `date_picker.png` — no green dates may be open yet, try again later |
| Task not running at 12 PM | Open Task Scheduler, find `ComfyDeskBooking`, check "Last Run Result" |
| PC was off at 12 PM | Run the script manually: `python ...\book_desk.py` |
| Want to verify task exists | Run in PowerShell: `schtasks /query /tn "ComfyDeskBooking"` |
| Want to delete the task | Run in PowerShell: `schtasks /delete /tn "ComfyDeskBooking" /f` |

---

## Requirements

- Windows 10/11
- Python 3.8 or higher
- Playwright — `pip install playwright`
- Chromium browser — `python -m playwright install chromium`
- BP network / VPN access (required for SSO login)

---

## Important Notes

- The saved session (`auth_state.json`) expires after a few weeks — re-run `--login` when it does
- The script only books **weekdays** (Mon–Fri) and skips Sat/Sun
- On **Monday**, it books all newly opened days at once (Sat + Sun each unlock one new day)
- Your PC must be **on and not in hibernation** at 12:00 PM for the scheduled task to fire
- If you move the `desk-booker` folder to a different location, re-run the `schtasks` command in Step 5 with the new path
