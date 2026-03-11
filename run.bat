@echo off
chcp 65001 > nul
echo ============================================
echo  PDF Szamla Nevesito - FUTTAT mod
echo ============================================
echo.
echo Fajlok feldolgozasa az 'input' mappaban...
echo Az atnevezett fajlok az 'output' mappaba kerulnek.
echo Excel osszesito a 'preview' mappaba kerul.
echo.
python main.py run
echo.
pause
