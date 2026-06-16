@echo off
echo Installing Playwright browser...
python -m playwright install chromium

echo.
echo Creating Windows Task Scheduler task (Mon-Fri at 12:00 PM)...

schtasks /create /tn "ComfyDeskBooking" ^
  /tr "python C:\Users\5874xe\Downloads\book_desk.py" ^
  /sc WEEKLY ^
  /d MON,TUE,WED,THU,FRI ^
  /st 12:00 ^
  /f

echo.
echo Done! Task "ComfyDeskBooking" created.
echo.
echo NEXT STEP: Run the one-time login first:
echo   python C:\Users\5874xe\Downloads\book_desk.py --login
pause
