@echo off
call .\venv\Scripts\activate

echo Please enter the input file path:
set /p input_file_path=

echo Please enter the output file path (or press Enter to use default):
set /p output_file_path=
if "%output_file_path%"=="" (
    set "output_file_path=output_reviews.csv"
)

echo Please wait...

python main.py --input %input_file_path% --output %output_file_path%
echo Process completed.
pause
