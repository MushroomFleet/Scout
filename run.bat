@echo off
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

echo Scout File Organizer
echo ===================
echo 1) Run Scout (Original)
echo 2) Run Scout2 (Enhanced)
echo.

set /p choice="Enter your choice (1-2): "

if "%choice%"=="1" (
    echo.
    echo Running Scout File Organizer (Original)...
    python scout.py
) else if "%choice%"=="2" (
    echo.
    echo Running Scout2 File Organizer (Enhanced)...
    python scout2.py
) else (
    echo.
    echo Invalid choice. Using Scout2 by default...
    python scout2.py
)

pause
