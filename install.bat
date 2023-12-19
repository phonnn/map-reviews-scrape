@echo off

set VENV_PATH=.\venv

echo Creating virtual environment...
python -m venv %VENV_PATH%

call %VENV_PATH%\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo Setup completed.
pause
