@echo off
echo ---------------------------------------
echo  START APLIKACJI: GML → SHP (Flask)
echo ---------------------------------------

REM Przejdź do folderu aplikacji
cd app

REM Utwórz środowisko jeśli nie istnieje
IF NOT EXIST "..\\venv" (
    echo Tworzenie środowiska wirtualnego...
    python -m venv ..\\venv
)

REM Aktywuj środowisko
call ..\\venv\\Scripts\\activate

REM Sprawdź czy Flask jest zainstalowany
pip show flask >nul 2>&1
IF ERRORLEVEL 1 (
    echo Instalacja wymaganych bibliotek...
    pip install flask geopandas shapely pyproj fiona
)

REM Uruchom aplikację
echo.
echo Aplikacja działa na: http://127.0.0.1:5000
echo.
python app.py

pause