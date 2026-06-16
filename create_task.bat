@echo off
schtasks /create /tn "ComfyDeskBooking" /tr "python C:\Users\5874xe\Downloads\desk-booker\book_desk.py" /sc WEEKLY /d MON,TUE,WED,THU,FRI /st 12:00 /f
echo.
echo Task "ComfyDeskBooking" created. It will run Mon-Fri at 12:00 PM.
pause
