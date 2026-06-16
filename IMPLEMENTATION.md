# Implementation Deep Dive — How the Desk Booking Automation Works

This document explains every part of the `book_desk.py` script in detail —
what each function does, what logic is used, how buttons are found and clicked,
and what skills you need to build this kind of automation yourself.

---

## Table of Contents

1. [Big Picture — What is Browser Automation?](#1-big-picture)
2. [Tech Stack — What Tools Are Used?](#2-tech-stack)
3. [Script Structure Overview](#3-script-structure)
4. [Constants — Configuration at the Top](#4-constants)
5. [Function: main()](#5-function-main)
6. [Function: login_and_save_session()](#6-function-login_and_save_session)
7. [Function: book_desk()](#7-function-book_desk)
   - [Step 1 — Navigate to the Page](#step-1--navigate-to-the-page)
   - [Step 2 — Open the Search Bar](#step-2--open-the-search-bar)
   - [Step 3 — Type the Desk Name](#step-3--type-the-desk-name)
   - [Step 4 — Click the Book Button](#step-4--click-the-book-button)
   - [Step 5 — Open the Date Picker](#step-5--open-the-date-picker)
   - [Step 6 — Select All Available Weekdays](#step-6--select-all-available-weekdays)
   - [Step 7 — Complete Booking](#step-7--complete-booking)
8. [How Selectors Work — Finding Buttons on a Page](#8-how-selectors-work)
9. [How SSO Login is Handled](#9-how-sso-login-is-handled)
10. [How Screenshots Help Debugging](#10-how-screenshots-help-debugging)
11. [How the Scheduler Works](#11-how-the-scheduler-works)
12. [Skills to Learn to Build This Yourself](#12-skills-to-learn)

---

## 1. Big Picture

A website like Comfy App is just HTML, CSS, and JavaScript running in a browser.
Normally a human opens the browser, clicks buttons, fills forms, and submits.

**Browser automation** means writing a script that does all of that programmatically —
it controls a real Chrome browser, finds elements on the page, and clicks/types into them,
exactly as a human would, but automatically.

The flow for this script is:
```
Run script
  → Open Chrome (invisible)
  → Load saved login session
  → Go to booking page
  → Search for desk 7S.009
  → Click Book
  → Select all available dates
  → Click Complete booking
  → Save screenshot
  → Close Chrome
```

---

## 2. Tech Stack

| Tool | What it is | Why we use it |
|------|-----------|---------------|
| **Python** | Programming language | Easy to read, huge library ecosystem |
| **Playwright** | Browser automation library | Controls Chrome, handles modern JS apps reliably |
| **asyncio** | Python's async framework | Playwright is async — lets actions run without blocking |
| **Windows Task Scheduler** | Windows built-in scheduler | Runs the script automatically at 12 PM every weekday |
| **pathlib.Path** | Python file path utility | Cross-platform way to build file paths |

### Why Playwright over Selenium?
Playwright is newer and handles modern Single Page Applications (SPAs) better.
Comfy App is a React/Vue-style app — it loads content dynamically with JavaScript.
Playwright waits for elements to appear automatically, while Selenium often needs manual waits.

---

## 3. Script Structure

```
book_desk.py
│
├── Constants (BOOKING_URL, DESK_NAME, AUTH_FILE)
│
├── login_and_save_session(page)
│     Opens visible browser, helps you log in via SSO,
│     saves session cookies to auth_state.json
│
├── book_desk(page)
│     The main automation — navigates, searches, selects dates, books
│
└── main(login_mode)
      Entry point — decides whether to login or book,
      sets up browser, calls the right function
```

---

## 4. Constants

```python
BOOKING_URL = "https://my.comfyapp.com/app/location"
COMPANY_ID  = "bp"
DESK_NAME   = "7s.009"
AUTH_FILE   = Path(__file__).parent / "auth_state.json"
```

- `BOOKING_URL` — the exact page the script navigates to
- `COMPANY_ID` — the company slug entered on the first login screen
- `DESK_NAME` — the desk to search for and book (change this to book a different desk)
- `AUTH_FILE` — path to the saved login session file, stored in the same folder as the script
  - `Path(__file__).parent` means "the folder this script lives in" — avoids hardcoded paths

---

## 5. Function: main()

```python
async def main(login_mode=False):
    async with async_playwright() as p:
        if login_mode or not AUTH_FILE.exists():
            browser = await p.chromium.launch(headless=False)  # visible browser
            ...
            await login_and_save_session(page)
        else:
            browser = await p.chromium.launch(headless=True)   # invisible browser
            context = await browser.new_context(storage_state=str(AUTH_FILE))
            ...
            await book_desk(page)
```

**What it does:**
- `async with async_playwright()` — starts the Playwright engine
- `headless=False` — opens a visible browser window (used for login so you can interact)
- `headless=True` — runs Chrome silently in the background (used for automated booking)
- `storage_state=str(AUTH_FILE)` — loads the saved cookies/session so you're already logged in
- `sys.exit(0 if success else 1)` — returns exit code 0 (success) or 1 (failure) to Task Scheduler

**How `--login` flag works:**
```python
login_mode = "--login" in sys.argv
```
`sys.argv` is the list of command-line arguments. If you run:
```
python book_desk.py --login
```
Then `sys.argv = ['book_desk.py', '--login']` and `"--login" in sys.argv` is `True`.

---

## 6. Function: login_and_save_session()

This function runs **once** to capture your login session.

```python
await page.goto("https://my.comfyapp.com")
await page.wait_for_timeout(3_000)   # wait 3 seconds for page to load
```

**Finding and filling the company ID input:**
```python
company_input = page.locator("input").first
val = await company_input.input_value()
if not val:
    await company_input.fill(COMPANY_ID)
    await page.keyboard.press("Enter")
```
- `page.locator("input").first` — finds the first `<input>` tag on the page
- `input_value()` — reads what's already typed (avoid re-filling if already filled)
- `fill()` — clears the field and types the value
- `keyboard.press("Enter")` — simulates pressing the Enter key

**Clicking the SSO button:**
```python
for label in ["Sign in with your organization", "Sign in", "Login", ...]:
    btn = page.get_by_role("button", name=label, exact=False)
    await btn.wait_for(timeout=4_000)
    await btn.click()
```
- `get_by_role("button", name=...)` — finds a button by its visible text
- `exact=False` — partial match (so "Sign in" matches "Sign in with your organization")
- We try multiple labels because the button text can vary — first one that works wins

**Saving the session:**
```python
await page.context.storage_state(path=str(AUTH_FILE))
```
This saves ALL cookies, localStorage, and sessionStorage from the browser to a JSON file.
Next time the script runs, it loads this file and Chrome thinks you're already logged in —
no SSO prompt needed.

---

## 7. Function: book_desk()

### Step 1 — Navigate to the Page

```python
await page.goto(BOOKING_URL, wait_until="networkidle", timeout=60_000)
```
- `wait_until="networkidle"` — waits until there are no more network requests for 500ms
  This ensures the JavaScript app has fully loaded before we start clicking
- `timeout=60_000` — give it up to 60 seconds (the app can be slow)

**Session expiry check:**
```python
if "login" in page.url or "auth" in page.url:
    print("ERROR: Session expired.")
    return False
```
If the app redirects you to a login page, the URL changes. We detect this and exit early.

---

### Step 2 — Open the Search Bar

```python
for selector in [
    "[aria-label*='search' i]",
    "[title*='search' i]",
    "button[class*='search']",
    "input[placeholder*='search' i]",
]:
    el = page.locator(selector).first
    await el.wait_for(timeout=3_000)
    await el.click()
```

We try multiple CSS selectors because we don't know exactly which one will match.
This is a **defensive approach** — try the most specific first, fall back to broader ones.

**What is a CSS Selector?**
It's a pattern that describes which HTML elements to find. Examples:
- `[aria-label*='search' i]` — any element whose `aria-label` attribute *contains* the word "search" (case-insensitive, that's what `i` means)
- `button[class*='search']` — a `<button>` element whose class name contains "search"
- `input[placeholder*='search' i]` — an `<input>` whose placeholder text contains "search"

---

### Step 3 — Type the Desk Name

```python
search_input = page.locator("input[type='text']:visible, input[type='search']:visible").first
await search_input.fill(DESK_NAME)
await page.wait_for_timeout(2_000)
```

- `:visible` — only match elements that are actually visible on screen (not hidden)
- We wait 2 seconds after typing for the search results to appear (the app fetches results as you type)

---

### Step 4 — Click the Book Button

After searching, a result row appears with the desk name and a "Book" button next to it.

```python
row = page.locator(f"text={DESK_NAME}").locator("xpath=ancestor::*[.//button][1]")
btn = row.locator("button").last
await btn.click()
```

**How this works:**
1. `text={DESK_NAME}` — find the element that contains the text "7s.009"
2. `xpath=ancestor::*[.//button][1]` — walk UP the HTML tree to find the nearest
   ancestor element that contains a `<button>` inside it (this is the result row)
3. `.locator("button").last` — within that row, get the last button (the Book button)

This is called **relative locating** — instead of trying to describe the button directly,
we find something we know (the desk name text) and navigate relative to it.

---

### Step 5 — Open the Date Picker

```python
for selector in [
    "label:has-text('Select Date') + *",
    "[class*='select-date']",
    "select",
]:
    el = page.locator(selector).first
    await el.wait_for(timeout=3_000)
    await el.click()
```

- `label:has-text('Select Date') + *` — find a `<label>` that says "Select Date",
  then `+` means "the very next sibling element" — that's the dropdown next to the label
- `:has-text()` — Playwright's custom pseudo-selector that matches by text content

---

### Step 6 — Select All Available Weekdays

This is the most complex part. The calendar renders each day as a `<button>`.

**Available days** (green) have this HTML:
```html
<button class="core-datepicker__date" aria-disabled="false"><span>25</span></button>
```

**Disabled/unavailable days** have:
```html
<button class="core-datepicker__date core-datepicker__date--disabled" aria-disabled="true">
```

So we select only the enabled ones:
```python
available_cells = await page.locator(
    "button.core-datepicker__date:not(.core-datepicker__date--disabled)[aria-disabled='false']"
).all()
```

Breaking down this selector:
- `button.core-datepicker__date` — a button with class `core-datepicker__date`
- `:not(.core-datepicker__date--disabled)` — exclude buttons that also have the disabled class
- `[aria-disabled='false']` — double-check the aria attribute is false (not disabled)

**Filtering to weekdays only:**
```python
for cell in available_cells:
    txt = (await cell.inner_text()).strip()   # get the day number text e.g. "25"
    day_num = int(txt)
    candidate = dt.date(year, month, day_num) # build a real date object
    if candidate.weekday() <= 4:              # 0=Mon, 1=Tue...4=Fri, 5=Sat, 6=Sun
        weekday_cells.append((candidate, cell))
```

`datetime.date.weekday()` returns 0 for Monday through 6 for Sunday.
We keep only days where weekday() is 0–4 (Mon–Fri).

**Clicking all of them:**
```python
weekday_cells.sort(key=lambda x: x[0])   # sort by date, oldest first
for target_date, target_cell in weekday_cells:
    await target_cell.click()
    await page.wait_for_timeout(500)
```

The calendar supports multi-select — each click toggles a date on/off.
Sorting ensures we click in chronological order.

---

### Step 7 — Complete Booking

```python
btn = page.locator(
    "button.hj-booking-desk-complete, button.booking-edit__button--primary, button[type='submit']"
).first
await btn.click()
```

We found the exact class name `hj-booking-desk-complete` by inspecting the HTML
(right-click → Inspect in browser DevTools). We also include fallbacks in case
the class name changes in a future app update.

---

## 8. How Selectors Work — Finding Buttons on a Page

Every element on a webpage has HTML like:
```html
<button class="booking-btn primary" aria-label="Book desk" type="submit">Book</button>
```

Playwright can find this element multiple ways:

| Method | Example | Matches when... |
|--------|---------|-----------------|
| CSS class | `button.booking-btn` | button has class "booking-btn" |
| Attribute | `[aria-label='Book desk']` | element has that exact aria-label |
| Text | `text=Book` | element's visible text is "Book" |
| Role | `get_by_role("button", name="Book")` | a button with accessible name "Book" |
| XPath | `//button[@type='submit']` | button with type="submit" |
| Partial attribute | `[class*='booking']` | class contains the word "booking" |

**How we discovered the right selectors:**
1. Open the website in Chrome
2. Right-click the element you want → click **Inspect**
3. DevTools highlights the HTML for that element
4. Read the `class`, `id`, `aria-label`, `type`, or text to build a selector
5. Test it in the DevTools Console: `document.querySelector('your-selector')`

---

## 9. How SSO Login is Handled

SSO (Single Sign-On) means your company (BP) controls the login.
When you click "Sign in with your organization", the browser redirects to
Microsoft's login server, which checks your Windows credentials and redirects back.

**Why we can't automate the SSO itself:**
Microsoft's login page has bot detection and MFA — we can't fake it.

**What we do instead:**
1. Run `--login` mode once — opens a real visible browser
2. You log in manually (Microsoft handles it, possibly auto-logs you in via Windows)
3. After login, we call `storage_state()` which saves all the cookies
4. Future runs load those cookies — the app thinks you're still logged in

**Why does the session eventually expire?**
Websites set an expiry on login cookies (typically 1–4 weeks for corporate apps).
After expiry, the cookie is invalid and you get redirected to login again.
Solution: re-run `--login` to get fresh cookies.

---

## 10. How Screenshots Help Debugging

At every key step the script saves a `.png` file:

| Screenshot | When saved | What to look for |
|-----------|-----------|-----------------|
| `login_step1.png` | After opening login page | Is the page loaded? Company ID field visible? |
| `login_step2.png` | After entering company ID | Is the SSO button visible? |
| `search_results.png` | After typing desk name | Is the desk listed with a Book button? |
| `before_book.png` | After clicking Book | Is the booking form open? |
| `date_picker.png` | After opening date picker | Are green dates visible? |
| `booking_confirmation.png` | After clicking Complete | Are the selected dates highlighted? |

When something fails, you look at the screenshot to see exactly what the browser saw —
this tells you which step broke and why.

---

## 11. How the Scheduler Works

Windows Task Scheduler is a built-in Windows feature that runs programs on a schedule.

We created the task with:
```
schtasks /create
  /tn "ComfyDeskBooking"          ← task name
  /tr "python ...book_desk.py"    ← command to run
  /sc WEEKLY                      ← schedule type
  /d MON,TUE,WED,THU,FRI         ← which days
  /st 12:00                       ← what time
  /f                              ← force overwrite if exists
```

At 12:00 PM every weekday, Windows runs `python book_desk.py` silently in the background.
The script opens an invisible Chrome, books the desk, saves a screenshot, and exits.

To check if it ran: open **Task Scheduler** from the Start menu → find `ComfyDeskBooking`
→ check "Last Run Time" and "Last Run Result" (0 = success).

---

## 12. Skills to Learn to Build This Yourself

Here is a roadmap from beginner to being able to build this kind of automation independently.

### Level 1 — Python Basics (1–2 weeks)
- Variables, strings, numbers, booleans
- If/else conditions and for loops
- Functions (`def`) and return values
- Lists and dictionaries
- Reading/writing files
- `import` — using libraries

**Resources:**
- https://www.learnpython.org (free, interactive)
- "Automate the Boring Stuff with Python" by Al Sweigart (free online)

### Level 2 — How Websites Work (2–3 days)
Understanding what you're automating is essential.
- What is HTML? (structure of a page)
- What is CSS? (styling — also how selectors work)
- What is JavaScript? (makes pages interactive)
- What are HTTP requests? (how browser talks to servers)
- What are cookies and sessions? (how login state is kept)

**Resource:** https://developer.mozilla.org/en-US/docs/Learn (MDN Web Docs)

### Level 3 — Browser DevTools (1–2 days)
The most important practical skill for web automation.
- Open DevTools: press **F12** in any browser
- **Elements tab** — inspect HTML, find class names and attributes
- **Console tab** — test selectors: `document.querySelector('.my-class')`
- **Network tab** — see API calls the page makes (useful for API automation)

**Practice:** Open any website, right-click elements, read their HTML.

### Level 4 — Playwright (1 week)
- Install: `pip install playwright`
- Official docs: https://playwright.dev/python/docs/intro
- Key concepts to learn:
  - `page.goto()` — navigate to a URL
  - `page.locator()` — find elements with CSS selectors
  - `page.get_by_role()`, `page.get_by_text()` — find elements semantically
  - `.click()`, `.fill()`, `.press()` — interact with elements
  - `.wait_for()`, `wait_for_timeout()` — handle timing
  - `page.screenshot()` — save screenshots
  - `browser_context.storage_state()` — save/load login sessions
  - `headless=True/False` — invisible vs visible browser

### Level 5 — Async Python (2–3 days)
Playwright uses `async/await` — this is Python's way of doing non-blocking operations.
- Understand `async def`, `await`, `asyncio.run()`
- Why it's used: waiting for a page to load shouldn't freeze your whole program

**Resource:** https://realpython.com/async-io-python/

### Level 6 — CSS Selectors In Depth (2–3 days)
This is what lets you find any element on any page.
- Tag selectors: `button`, `input`, `div`
- Class selectors: `.my-class`
- Attribute selectors: `[type='submit']`, `[aria-label*='search']`
- Combinators: `div > button` (direct child), `label + input` (next sibling)
- Pseudo-classes: `:not()`, `:first-child`, `:visible`

**Practice tool:** https://css-selector-tester.com

### Level 7 — XPath (optional, 1–2 days)
XPath is an alternative to CSS selectors, more powerful for navigating up the HTML tree.
- We used: `xpath=ancestor::*[.//button][1]` — walk up to find a parent that has a button
- CSS can't traverse upward; XPath can — useful for "find the container of this element"

### Bonus — What to Build for Practice
1. **Google search automation** — open Google, search something, print the first 5 results
2. **Form filler** — automatically fill a contact form on a test site
3. **Price tracker** — check a product price daily and save it to a file
4. **Login automation** — log into a site (that you own) and take a screenshot of your profile

---

## Summary

This script works by:
1. Controlling a real Chrome browser with Playwright
2. Saving your login cookies once so it never needs to log in again
3. Finding page elements using CSS selectors discovered via browser DevTools
4. Using defensive coding (try multiple selectors, take screenshots) to handle UI changes
5. Using Python's `datetime` library to figure out which calendar days are weekdays
6. Running automatically via Windows Task Scheduler every weekday at noon

The core skill is **knowing how to read HTML** and **translate what you see on screen
into a selector** that code can use to find and click the right element.
