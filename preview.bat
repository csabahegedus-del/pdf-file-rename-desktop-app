@echo off
chcp 65001 > nul
echo ============================================
echo  PDF Szamla Nevesito - ELONEZET mod
echo ============================================
echo.
echo Fajlok elemzese az 'input' mappaban...
echo Eredmeny Excel fajlkent a 'preview' mappaba kerul.
echo A PDF fajlok NEM kerulnek modositasra.
echo.
python main.py preview
echo.
pause
