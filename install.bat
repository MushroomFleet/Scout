@echo off
echo Creating Python virtual environment...
python -m venv venv
echo.

echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

echo Installing required packages...
pip install -r requirements.txt
echo.

echo Setup complete! You can now run the script using run.bat
pause
