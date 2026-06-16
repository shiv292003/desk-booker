"""
Comfy desk booking automation — books desk 7s.009 via SSO (BP).
Run manually once first to save the authenticated session to auth_state.json.
Scheduled runs reuse that saved session so no login is needed each time.
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BOOKING_URL = "https://my.comfyapp.com/app/location"
COMPANY_ID   = "bp"          # company slug on the first login screen
DESK_NAME    = "7s.009"
AUTH_FILE    = Path(__file__).parent / "auth_state.json"


async def login_and_save_session(page):
    """Interactive login — run once to capture the SSO session."""
    print("Opening login page…")
    await page.goto("https://my.comfyapp.com")
    await page.wait_for_timeout(3_000)

    # Screenshot so we can see what's on the page
    shot = Path(__file__).parent / "login_step1.png"
    await page.screenshot(path=str(shot))
    print(f"Screenshot saved: {shot}")

    # Step 1 — enter company ID if an input box is present
    try:
        company_input = page.locator("input").first
        await company_input.wait_for(timeout=5_000)
        val = await company_input.input_value()
        if not val:
            await company_input.fill(COMPANY_ID)
            print(f"Filled company ID: {COMPANY_ID}")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(2_000)
    except PWTimeout:
        pass  # already past company ID screen

    # Screenshot after company ID step
    shot2 = Path(__file__).parent / "login_step2.png"
    await page.screenshot(path=str(shot2))
    print(f"Screenshot saved: {shot2}")

    # Step 2 — click any SSO/sign-in button (try multiple labels)
    clicked = False
    for label in [
        "Sign in with your organization",
        "your company will authenticate you",
        "Sign in",
        "Login",
        "Continue",
        "Next",
    ]:
        try:
            btn = page.get_by_role("button", name=label, exact=False)
            await btn.wait_for(timeout=4_000)
            await btn.click()
            print(f"Clicked button: '{label}'")
            clicked = True
            break
        except PWTimeout:
            continue

    if not clicked:
        # Last resort — click the first visible button
        try:
            btn = page.locator("button").first
            await btn.wait_for(timeout=5_000)
            text = await btn.inner_text()
            await btn.click()
            print(f"Clicked first button on page: '{text.strip()}'")
        except PWTimeout:
            print("WARNING: Could not find any button. Check login_step2.png and complete login manually in the browser.")

    # Wait for user to complete SSO in the browser (Microsoft login)
    print("\n>>> Browser is open. Complete your company SSO login in the browser window.")
    print(">>> Once you are fully logged in and see the main app, come back here and press Enter. <<<")
    input()

    await page.context.storage_state(path=str(AUTH_FILE))
    print(f"Session saved to {AUTH_FILE}")


async def book_desk(page):
    """Book desk 7s.009 for today using a saved session."""
    print(f"Navigating to {BOOKING_URL}…")
    await page.goto(BOOKING_URL, wait_until="networkidle", timeout=60_000)

    # If redirected to login, session expired
    if "login" in page.url or "auth" in page.url:
        print("ERROR: Session expired. Run with --login to re-authenticate.")
        return False

    print("Page loaded. Looking for desk search…")
    await page.wait_for_timeout(3_000)

    # Click the search/magnifying glass icon on the map
    search_opened = False
    for selector in [
        "[aria-label*='search' i]",
        "[title*='search' i]",
        "button svg[data-icon*='search']",
        "button[class*='search']",
        "input[placeholder*='search' i]",
        "input[placeholder*='desk' i]",
        "input[placeholder*='find' i]",
    ]:
        try:
            el = page.locator(selector).first
            await el.wait_for(timeout=3_000)
            await el.click()
            print(f"Clicked search element: {selector}")
            search_opened = True
            await page.wait_for_timeout(1_000)
            break
        except PWTimeout:
            continue

    # Type the desk name into whatever input is now focused
    if search_opened:
        try:
            search_input = page.locator("input[type='text']:visible, input[type='search']:visible, input:not([type]):visible").first
            await search_input.wait_for(timeout=5_000)
            await search_input.fill(DESK_NAME)
            print(f"Typed '{DESK_NAME}' in search box.")
            await page.wait_for_timeout(2_000)

            # Screenshot to see results
            shot = Path(__file__).parent / "search_results.png"
            await page.screenshot(path=str(shot))
            print(f"Search results screenshot: {shot}")

            # Click the Book button in the search result row (next to the desk name)
            book_clicked = False
            for selector in [
                f"text={DESK_NAME} >> .. >> button",
                f"text={DESK_NAME} >> xpath=.. >> button",
            ]:
                try:
                    btn = page.locator(selector).first
                    await btn.wait_for(timeout=3_000)
                    await btn.click()
                    print(f"Clicked Book button in search result row via {selector}")
                    book_clicked = True
                    await page.wait_for_timeout(2_000)
                    break
                except PWTimeout:
                    continue

            # Fallback: find the row containing desk name and click its button
            if not book_clicked:
                try:
                    row = page.locator(f"text={DESK_NAME}").locator("xpath=ancestor::*[.//button][1]")
                    btn = row.locator("button").last
                    await btn.wait_for(timeout=3_000)
                    await btn.click()
                    print("Clicked Book button via ancestor row.")
                    book_clicked = True
                    await page.wait_for_timeout(2_000)
                except PWTimeout:
                    pass

            if not book_clicked:
                # Last resort: click the desk name to open popup
                result = page.locator(f"text={DESK_NAME}").first
                await result.wait_for(timeout=3_000)
                await result.click()
                print(f"Clicked desk name as fallback.")
                await page.wait_for_timeout(2_000)
        except PWTimeout:
            print("Could not find search input after clicking search icon.")

    # Screenshot to see current state
    shot = Path(__file__).parent / "before_book.png"
    await page.screenshot(path=str(shot))
    print(f"Before-book screenshot: {shot}")

    await page.wait_for_timeout(2_000)

    import datetime
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_fmt = tomorrow.strftime("%b %d, %y").replace(" 0", " ")
    tomorrow_fmt2 = tomorrow.strftime("%b %d, %y")
    print(f"Opening date picker to find last available date…")

    # The date selector is a dropdown — click it to open
    date_opened = False
    for selector in [
        "[class*='select-date']",
        "[class*='date'] select",
        "select",
        "[class*='date-picker']",
        "label:has-text('Select Date') + *",
        "text=Select Date >> xpath=.. >> *[last()]",
    ]:
        try:
            el = page.locator(selector).first
            await el.wait_for(timeout=3_000)
            await el.click()
            print(f"Clicked date selector via {selector}")
            date_opened = True
            await page.wait_for_timeout(1_000)
            break
        except PWTimeout:
            continue

    # Take screenshot to see what the date picker looks like
    shot = Path(__file__).parent / "date_picker.png"
    await page.screenshot(path=str(shot))
    print(f"Date picker screenshot: {shot}")

    # Try selecting from a <select> dropdown
    date_selected = False
    try:
        sel = page.locator("select").first
        await sel.wait_for(timeout=3_000)
        # Try selecting by visible text
        for fmt in [tomorrow_fmt, tomorrow_fmt2, str(tomorrow)]:
            try:
                await sel.select_option(label=fmt)
                print(f"Selected date from <select>: {fmt}")
                date_selected = True
                break
            except Exception:
                continue
    except PWTimeout:
        pass

    # Click ALL available weekday dates — handles Mon when Sat+Sun both opened new days
    if not date_selected:
        try:
            import datetime as dt
            today = dt.date.today()
            month = today.month
            year = today.year

            available_cells = await page.locator("button.core-datepicker__date:not(.core-datepicker__date--disabled)[aria-disabled='false']").all()
            print(f"Found {len(available_cells)} available day(s) on calendar.")

            weekday_cells = []
            for cell in available_cells:
                try:
                    txt = (await cell.inner_text()).strip()
                    if txt.isdigit():
                        day_num = int(txt)
                        try:
                            candidate = dt.date(year, month, day_num)
                        except ValueError:
                            continue
                        if candidate < today:
                            if month == 12:
                                candidate = dt.date(year + 1, 1, day_num)
                            else:
                                candidate = dt.date(year, month + 1, day_num)
                        if candidate.weekday() <= 4:  # Mon-Fri only
                            weekday_cells.append((candidate, cell))
                except Exception:
                    continue

            weekday_cells.sort(key=lambda x: x[0])

            if weekday_cells:
                # Click ALL available weekday dates (e.g. Monday may have 2 open)
                for target_date, target_cell in weekday_cells:
                    await target_cell.click()
                    print(f"Selected date: {target_date}")
                    await page.wait_for_timeout(500)
                date_selected = True
            elif available_cells:
                await available_cells[-1].click()
                print("Clicked last available day (weekday check failed).")
                date_selected = True
        except Exception as e:
            print(f"Error finding available days: {e}")

    if not date_selected:
        print("WARNING: Could not select date — check date_picker.png")

    await page.wait_for_timeout(1_000)

    # Click Complete booking
    booked = False
    try:
        btn = page.locator("button.hj-booking-desk-complete, button.booking-edit__button--primary, button[type='submit']").first
        await btn.wait_for(timeout=5_000)
        await btn.click()
        print("Clicked 'Complete booking'.")
        booked = True
    except PWTimeout:
        print("Could not find the Complete booking button — check before_book.png")

    # Final confirmation screenshot
    await page.wait_for_timeout(3_000)
    shot = Path(__file__).parent / "booking_confirmation.png"
    await page.screenshot(path=str(shot))
    print(f"Done! Confirmation screenshot: {shot}")
    return booked


async def main(login_mode=False):
    async with async_playwright() as p:
        if login_mode or not AUTH_FILE.exists():
            # Launch visible browser for interactive SSO
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            await login_and_save_session(page)
            await browser.close()
            print("\nLogin complete. Run the script again (without --login) to book the desk.")
        else:
            # Reuse saved session — run headless
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=str(AUTH_FILE))
            page = await context.new_page()
            success = await book_desk(page)
            await browser.close()
            sys.exit(0 if success else 1)


if __name__ == "__main__":
    login_mode = "--login" in sys.argv
    asyncio.run(main(login_mode))
