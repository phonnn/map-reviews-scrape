@echo off
call .\venv\Scripts\activate

pip install -r requirements.txt

python app.py
pause
